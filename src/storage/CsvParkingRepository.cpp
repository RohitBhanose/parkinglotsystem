#include "storage/CsvParkingRepository.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>

#include "config/KeyValueFile.hpp"
#include "exceptions/ParkingException.hpp"
#include "models/ParkingTransaction.hpp"
#include "models/Vehicle.hpp"

namespace fs = std::filesystem;

namespace parking {

namespace {

const std::vector<std::string> kLegacyHeader = {"Number Plate", "Entry Time", "Exit Time", "Slot"};

const std::vector<std::string> kHeader = {
    "Number Plate", "Entry Time",  "Exit Time",   "Slot",        "Transaction ID", "Vehicle Type",
    "Status",       "Base Minutes", "Peak Minutes", "Base Rate", "Peak Rate",      "Base Amount",
    "Peak Amount",  "Total Fare",  "Payment Method", "Payment Status", "Payment Time",
};

enum Column {
    kPlate, kEntry, kExit, kSlot, kId, kType, kStatus, kBaseMinutes, kPeakMinutes,
    kBaseRate, kPeakRate, kBaseAmount, kPeakAmount, kTotalFare, kPayMethod, kPayStatus, kPayTime,
};

// Splits one CSV line, honouring "quoted, fields" (pandas may write those).
std::vector<std::string> splitCsvLine(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (quoted) {
            if (c == '"' && i + 1 < line.size() && line[i + 1] == '"') {
                field += '"';
                ++i;
            } else if (c == '"') {
                quoted = false;
            } else {
                field += c;
            }
        } else if (c == '"') {
            quoted = true;
        } else if (c == ',') {
            fields.push_back(trim(field));
            field.clear();
        } else {
            field += c;
        }
    }
    fields.push_back(trim(field));
    return fields;
}

bool parseLong(const std::string& text, long long& out) {
    std::istringstream in(text);
    return static_cast<bool>(in >> out) && (in >> std::ws).eof();
}

bool parseDouble(const std::string& text, double& out) {
    std::istringstream in(text);
    return static_cast<bool>(in >> out) && (in >> std::ws).eof();
}

std::string money(double value) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(2) << value;
    return out.str();
}

std::string rate(double value) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(4) << value;
    return out.str();
}

// Parses one data row. Returns an error message, or "" on success.
std::string parseRow(const std::vector<std::string>& f, bool legacy, int rowIndex, TransactionRecord& r) {
    const std::size_t expected = legacy ? kLegacyHeader.size() : kHeader.size();
    if (f.size() != expected) {
        return "expected " + std::to_string(expected) + " columns, found " + std::to_string(f.size());
    }

    r.numberPlate = Vehicle::normalizePlate(f[kPlate]);
    if (!Vehicle::isValidPlate(r.numberPlate)) {
        return "invalid number plate '" + f[kPlate] + "'";
    }
    const auto entry = timeutil::parseCsv(f[kEntry]);
    if (!entry) {
        return "invalid entry time '" + f[kEntry] + "'";
    }
    r.entryTime = *entry;
    if (!f[kExit].empty()) {
        r.exitTime = timeutil::parseCsv(f[kExit]);
        if (!r.exitTime) {
            return "invalid exit time '" + f[kExit] + "'";
        }
    }
    r.slotNumber = f[kSlot];
    if (r.slotNumber.empty()) {
        return "missing slot number";
    }

    if (legacy) {
        // The original app wrote no id/status/fee: ids follow row order and the
        // status follows from whether an exit time was recorded.
        r.transactionId = rowIndex;
        r.vehicleType = "CAR";
        r.status = r.exitTime ? "COMPLETED" : "ACTIVE";
        return "";
    }

    long long id = 0;
    if (!parseLong(f[kId], id) || id <= 0) {
        return "invalid transaction id '" + f[kId] + "'";
    }
    r.transactionId = static_cast<int>(id);
    r.vehicleType = f[kType];
    if (!isSupportedVehicleType(r.vehicleType)) {
        return "unknown vehicle type '" + f[kType] + "'";
    }
    r.status = f[kStatus];
    if (!parseTransactionStatus(r.status)) {
        return "unknown status '" + f[kStatus] + "'";
    }

    if (!f[kTotalFare].empty()) {
        FeeBreakdown fee;
        if (!parseLong(f[kBaseMinutes], fee.baseMinutes) || !parseLong(f[kPeakMinutes], fee.peakMinutes) ||
            !parseDouble(f[kBaseRate], fee.baseRate) || !parseDouble(f[kPeakRate], fee.peakRate) ||
            !parseDouble(f[kBaseAmount], fee.baseAmount) || !parseDouble(f[kPeakAmount], fee.peakAmount) ||
            !parseDouble(f[kTotalFare], fee.totalAmount)) {
            return "invalid fee columns";
        }
        fee.totalMinutes = r.exitTime ? (*r.exitTime - r.entryTime).count() : 0;
        r.fee = fee;
    }

    r.paymentMethod = f[kPayMethod];
    r.paymentStatus = f[kPayStatus];
    if (!f[kPayTime].empty()) {
        r.paymentTime = timeutil::parseCsv(f[kPayTime]);
        if (!r.paymentTime) {
            return "invalid payment time '" + f[kPayTime] + "'";
        }
    }
    return "";
}

std::string formatRow(const TransactionRecord& r) {
    std::vector<std::string> f(kHeader.size());
    f[kPlate] = r.numberPlate;
    f[kEntry] = timeutil::formatCsv(r.entryTime);
    f[kExit] = r.exitTime ? timeutil::formatCsv(*r.exitTime) : "";
    f[kSlot] = r.slotNumber;
    f[kId] = std::to_string(r.transactionId);
    f[kType] = r.vehicleType;
    f[kStatus] = r.status;
    if (r.fee) {
        f[kBaseMinutes] = std::to_string(r.fee->baseMinutes);
        f[kPeakMinutes] = std::to_string(r.fee->peakMinutes);
        f[kBaseRate] = rate(r.fee->baseRate);
        f[kPeakRate] = rate(r.fee->peakRate);
        f[kBaseAmount] = money(r.fee->baseAmount);
        f[kPeakAmount] = money(r.fee->peakAmount);
        f[kTotalFare] = money(r.fee->totalAmount);
    }
    f[kPayMethod] = r.paymentMethod;
    f[kPayStatus] = r.paymentStatus;
    f[kPayTime] = r.paymentTime ? timeutil::formatCsv(*r.paymentTime) : "";

    std::string line;
    for (std::size_t i = 0; i < f.size(); ++i) {
        line += (i == 0 ? "" : ",") + f[i];
    }
    return line;
}

}  // namespace

CsvParkingRepository::CsvParkingRepository(std::string path) : path_(std::move(path)) {
    if (path_.empty()) {
        throw ValidationException("CSV path must not be empty");
    }
}

std::vector<TransactionRecord> CsvParkingRepository::loadTransactions() {
    readFile();
    return records_;
}

void CsvParkingRepository::readFile() {
    records_.clear();
    preservedLines_.clear();
    warnings_.clear();
    legacyFormat_ = false;
    // Only a fully successful read may mark the cache as loaded; otherwise a
    // later save would overwrite a file that was never understood.
    loaded_ = false;

    std::error_code ec;
    if (!fs::exists(path_, ec)) {
        loaded_ = true;  // no records yet - the file is created by the first save
        return;
    }
    std::ifstream in(path_);
    if (!in) {
        throw StorageException("Cannot open '" + path_ + "' for reading");
    }

    std::string line;
    if (!std::getline(in, line)) {
        loaded_ = true;  // empty file
        return;
    }
    if (line.rfind("\xEF\xBB\xBF", 0) == 0) {
        line.erase(0, 3);
    }
    const auto header = splitCsvLine(trim(line));
    if (header == kLegacyHeader) {
        legacyFormat_ = true;
    } else if (header != kHeader) {
        // Unknown layout: refuse to touch it rather than risk overwriting it.
        throw StorageException("'" + path_ + "' does not have a recognised parking-record header");
    }

    std::set<int> seenIds;
    int lineNumber = 1;
    int rowIndex = 0;
    while (std::getline(in, line)) {
        ++lineNumber;
        const std::string trimmed = trim(line);
        if (trimmed.empty()) {
            continue;
        }
        ++rowIndex;
        TransactionRecord record;
        std::string error = parseRow(splitCsvLine(trimmed), legacyFormat_, rowIndex, record);
        if (error.empty() && !seenIds.insert(record.transactionId).second) {
            error = "duplicate transaction id " + std::to_string(record.transactionId);
        }
        if (!error.empty()) {
            warnings_.push_back(path_ + ":" + std::to_string(lineNumber) + ": skipped malformed row (" + error + ")");
            preservedLines_.push_back(trimmed);
            continue;
        }
        records_.push_back(record);
    }
    if (in.bad()) {
        throw StorageException("Error while reading '" + path_ + "'");
    }
    loaded_ = true;
}

void CsvParkingRepository::saveTransaction(const TransactionRecord& record) {
    if (!loaded_) {
        readFile();
    }
    auto it = std::find_if(records_.begin(), records_.end(),
                           [&record](const TransactionRecord& r) { return r.transactionId == record.transactionId; });
    if (it == records_.end()) {
        records_.push_back(record);
    } else {
        *it = record;
    }
    writeFile();
}

void CsvParkingRepository::writeFile() {
    std::error_code ec;
    if (legacyFormat_) {
        const std::string backup = path_ + ".legacy-backup";
        if (!fs::exists(backup, ec)) {
            fs::copy_file(path_, backup, ec);
            if (ec) {
                throw StorageException("Could not back up '" + path_ + "' before upgrading it: " + ec.message());
            }
        }
    }

    const std::string tempPath = path_ + ".tmp";
    {
        std::ofstream out(tempPath, std::ios::trunc);
        if (!out) {
            throw StorageException("Cannot open '" + tempPath + "' for writing");
        }
        for (std::size_t i = 0; i < kHeader.size(); ++i) {
            out << (i == 0 ? "" : ",") << kHeader[i];
        }
        out << '\n';
        for (const auto& record : records_) {
            out << formatRow(record) << '\n';
        }
        for (const auto& raw : preservedLines_) {
            out << raw << '\n';
        }
        out.flush();
        if (!out) {
            fs::remove(tempPath, ec);
            throw StorageException("Failed while writing '" + tempPath + "'");
        }
    }

    fs::rename(tempPath, path_, ec);
    if (ec) {
        fs::remove(tempPath, ec);
        throw StorageException("Could not replace '" + path_ + "': " + ec.message());
    }
    legacyFormat_ = false;
}

}  // namespace parking
