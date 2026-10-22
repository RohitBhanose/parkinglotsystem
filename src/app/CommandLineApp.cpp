#include "app/CommandLineApp.hpp"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <filesystem>
#include <ostream>

#include "app/DemoRunner.hpp"
#include "app/JsonWriter.hpp"
#include "exceptions/ParkingException.hpp"
#include "services/ParkingFeeStrategy.hpp"
#include "services/ParkingLot.hpp"
#include "services/ParkingRecordManager.hpp"
#include "storage/CsvParkingRepository.hpp"
#ifdef PARKING_WITH_MYSQL
#include "storage/MySqlParkingRepository.hpp"
#endif

namespace parking {

namespace {

const char* const kDefaultConfigPath = "config/parking.cfg";

bool isInteger(const std::string& text) {
    std::size_t start = (!text.empty() && text[0] == '-') ? 1 : 0;
    if (start == text.size()) {
        return false;
    }
    for (std::size_t i = start; i < text.size(); ++i) {
        if (!std::isdigit(static_cast<unsigned char>(text[i]))) {
            return false;
        }
    }
    return text.size() <= 19;
}

std::string formatMoney(double amount) {
    char buffer[32];
    std::snprintf(buffer, sizeof(buffer), "%.2f", amount);
    return buffer;
}

JsonObject feeJson(const FeeBreakdown& fee) {
    JsonObject json;
    json.add("total_duration", fee.totalMinutes)
        .add("base_minutes", fee.baseMinutes)
        .add("base_rate", fee.baseRate, 4)
        .add("base_amount", fee.baseAmount)
        .add("peak_minutes", fee.peakMinutes)
        .add("peak_rate", fee.peakRate, 4)
        .add("peak_amount", fee.peakAmount)
        .add("total_amount", fee.totalAmount)
        .add("is_rush_hour", fee.isRushHour());
    return json;
}

void addOptionalTime(JsonObject& json, const std::string& key, const std::optional<TimePoint>& time) {
    if (time) {
        json.add(key, timeutil::toUnix(*time));
    } else {
        json.addNull(key);
    }
}

}  // namespace

CommandLineApp::CommandLineApp(std::ostream& out, std::ostream& err) : out_(out), err_(err) {}

std::string CommandLineApp::Options::get(const std::string& name, const std::string& fallback) const {
    auto it = named.find(name);
    return it == named.end() ? fallback : it->second;
}

bool CommandLineApp::parseOptions(const std::vector<std::string>& args, Options& options, std::string& error) {
    for (std::size_t i = 0; i < args.size(); ++i) {
        if (args[i].rfind("--", 0) == 0) {
            if (i + 1 >= args.size()) {
                error = "Option " + args[i] + " needs a value";
                return false;
            }
            options.named[args[i].substr(2)] = args[i + 1];
            ++i;
        } else {
            options.positional.push_back(args[i]);
        }
    }
    if (options.positional.empty()) {
        error = "No command given";
        return false;
    }
    return true;
}

int CommandLineApp::run(const std::vector<std::string>& args) {
    if (args.empty()) {
        out_ << "ERROR=Invalid input\n";  // same reply as parkinglot.c with too few arguments
        err_ << "Run 'parkinglot help' for usage.\n";
        return 1;
    }
    if (isInteger(args[0])) {
        return runLegacyFare(args);
    }
    Options options;
    std::string error;
    if (!parseOptions(args, options, error)) {
        return usageError(error);
    }
    return runCommand(options);
}

// Byte-for-byte compatible with the original parkinglot.c output, so any
// caller of the old executable keeps working.
int CommandLineApp::runLegacyFare(const std::vector<std::string>& args) {
    if (args.size() < 2 || !isInteger(args[1])) {
        out_ << "ERROR=Invalid input\n";
        return 1;
    }
    const long long entry = std::stoll(args[0]);
    const long long exit = std::stoll(args[1]);
    if (exit <= entry) {
        out_ << "ERROR=Invalid time\n";
        return 1;
    }
    if (args.size() >= 3 && args[2] == "cancel") {
        out_ << "STATUS=CANCELLED\nAMOUNT=0\n";
        return 0;
    }

    try {
        const AppConfig config = loadConfig(Options{});
        const auto strategy = createFeeStrategy(config, FourWheeler::TYPE_CODE);
        const FeeBreakdown fee = strategy->calculateFee(timeutil::fromUnix(entry), timeutil::fromUnix(exit));

        char buffer[512];
        std::snprintf(buffer, sizeof(buffer),
                      "STATUS=ACTIVE\nTOTAL_DURATION=%lld\nBASE_MINUTES=%lld\nBASE_RATE=%.2f\nBASE_AMOUNT=%.2f\n"
                      "PEAK_MINUTES=%lld\nPEAK_SURCHARGE=%.2f\nPEAK_AMOUNT=%.2f\nTOTAL_AMOUNT=%.2f\n",
                      fee.totalMinutes, fee.baseMinutes, fee.baseRate, fee.baseAmount, fee.peakMinutes,
                      fee.peakRate, fee.peakAmount, fee.totalAmount);
        out_ << buffer;
        return 0;
    } catch (const std::exception& e) {
        out_ << "ERROR=" << e.what() << '\n';
        return 1;
    }
}

int CommandLineApp::usageError(const std::string& message) {
    JsonObject reply;
    reply.add("ok", false).add("error_code", "USAGE_ERROR").add("message", message);
    out_ << reply.str() << '\n';
    err_ << message << "\nRun 'parkinglot help' for usage.\n";
    return 1;
}

int CommandLineApp::runCommand(const Options& options) {
    try {
        return dispatch(options);
    } catch (const ParkingException& e) {
        JsonObject reply;
        reply.add("ok", false).add("error_code", e.code()).add("message", e.what());
        out_ << reply.str() << '\n';
        return 1;
    } catch (const std::exception& e) {
        JsonObject reply;
        reply.add("ok", false).add("error_code", "INTERNAL_ERROR").add("message", e.what());
        out_ << reply.str() << '\n';
        return 1;
    }
}

AppConfig CommandLineApp::loadConfig(const Options& options) const {
    if (options.has("config")) {
        return AppConfig::loadFromFile(options.get("config"));
    }
    std::error_code ec;
    if (std::filesystem::exists(kDefaultConfigPath, ec)) {
        return AppConfig::loadFromFile(kDefaultConfigPath);
    }
    return AppConfig::defaults();
}

std::unique_ptr<ParkingRepository> CommandLineApp::makeRepository(const AppConfig& config,
                                                                  const Options& options) const {
    const std::string backend = options.get("backend", config.getStorageBackend());
    if (backend == "csv") {
        return std::make_unique<CsvParkingRepository>(options.get("data", config.getDataFile()));
    }
    if (backend == "mysql") {
#ifdef PARKING_WITH_MYSQL
        return std::make_unique<MySqlParkingRepository>(MySqlSettings::fromEnvironment());
#else
        throw DatabaseException("This build has no MySQL support; rebuild with -DPARKING_WITH_MYSQL=ON (see README)");
#endif
    }
    throw ValidationException("Unknown storage backend '" + backend + "' (expected csv or mysql)");
}

JsonObject CommandLineApp::transactionJson(const ParkingTransaction& transaction, const ParkingLot& lot) const {
    JsonObject json;
    json.add("session_id", transaction.getTransactionId())
        .add("number_plate", transaction.getVehicle().getNumberPlate())
        .add("vehicle_type", transaction.getVehicle().getVehicleType())
        .add("slot_number", transaction.getSlotNumber());
    if (const ParkingSlot* slot = lot.findSlot(transaction.getSlotNumber())) {
        json.add("zone", std::string(1, slot->getZone())).add("floor", slot->getFloor());
    } else {
        json.addNull("zone").addNull("floor");
    }
    addOptionalTime(json, "entry_time", transaction.getEntryTime());
    addOptionalTime(json, "exit_time", transaction.getExitTime());
    if (transaction.getExitTime()) {
        json.add("duration_seconds", transaction.calculateDuration());
    } else {
        json.addNull("duration_seconds");
    }

    if (const auto& fee = transaction.getFee()) {
        json.add("base_minutes", fee->baseMinutes)
            .add("peak_minutes", fee->peakMinutes)
            .add("base_amount", fee->baseAmount)
            .add("peak_amount", fee->peakAmount)
            .add("total_fare", fee->totalAmount)
            .add("is_rush_hour", fee->isRushHour());
    } else {
        json.addNull("base_minutes").addNull("peak_minutes").addNull("base_amount").addNull("peak_amount");
        json.addNull("total_fare").add("is_rush_hour", false);
    }
    json.add("session_status", toString(transaction.getStatus()));

    // Session-level payment status, using the same words as the MySQL schema.
    const auto& payment = transaction.getPayment();
    std::string paymentStatus = "PENDING";
    if (transaction.getStatus() == TransactionStatus::Cancelled) {
        paymentStatus = "WAIVED";
    } else if (payment && payment->getPaymentStatus() == PaymentStatus::Success) {
        paymentStatus = "PAID";
    }
    json.add("payment_status", paymentStatus);
    if (payment) {
        json.add("payment_method", toString(payment->getPaymentMethod()));
        addOptionalTime(json, "payment_time", payment->getPaymentTime());
    } else {
        json.addNull("payment_method").addNull("payment_time");
    }
    return json;
}

void CommandLineApp::printHelp() const {
    out_ << "parkinglot - C++ core of the Smart Parking Management System\n\n"
            "Legacy fare mode (same output as the original parkinglot.c):\n"
            "  parkinglot <entry_unix_ts> <exit_unix_ts> [cancel]\n\n"
            "JSON commands:\n"
            "  rates                                  tariff and peak-window settings\n"
            "  fare <entry_ts> <exit_ts> [--type CAR|BIKE]\n"
            "  slots                                  every slot with its status\n"
            "  entry <plate> [--type CAR|BIKE] [--at <unix_ts>]\n"
            "  exit <plate> [--method CASH|UPI|CARD] [--at <unix_ts>]\n"
            "  cancel <plate> [--at <unix_ts>]\n"
            "  active <plate>                         the plate's active session, if any\n"
            "  history [--plate <plate>] [--limit N]\n\n"
            "Console commands:\n"
            "  status                                 human-readable slot status\n"
            "  demo                                   OOP concept demonstration\n\n"
            "Options:\n"
            "  --config <file>    default: config/parking.cfg if present, else built-in defaults\n"
            "  --data <file>      CSV file (default from config: parking_data.csv)\n"
            "  --backend csv|mysql\n";
}

int CommandLineApp::dispatch(const Options& options) {
    const std::string& command = options.positional[0];

    if (command == "help" || command == "--help") {
        printHelp();
        return 0;
    }
    if (command == "demo") {
        DemoRunner(out_).run();
        return 0;
    }

    const AppConfig config = loadConfig(options);
    const std::string vehicleType = options.get("type", FourWheeler::TYPE_CODE);

    if (command == "rates") {
        const auto& window = config.getPeakWindow();
        JsonObject rates;
        for (const auto& [type, card] : config.getRateCards()) {
            JsonObject entry;
            entry.add("base_rate", card.baseRate, 4).add("peak_rate", card.peakRate, 4);
            rates.add(type, entry);
        }
        const auto carStrategy = createFeeStrategy(config, FourWheeler::TYPE_CODE);
        const RateCard& car = config.rateFor(FourWheeler::TYPE_CODE);
        JsonObject reply;
        reply.add("ok", true)
            .add("engine", "C++ parking core")
            .add("config_source", config.getSource())
            .add("lot_name", config.getLotName())
            .add("fee_strategy", carStrategy->getName())
            .add("description", carStrategy->describe())
            .add("base_rate", config.getFeeStrategyName() == "flat" ? config.getFlatRatePerMinute() : car.baseRate, 4)
            .add("peak_rate", config.getFeeStrategyName() == "flat" ? config.getFlatRatePerMinute() : car.peakRate, 4)
            .add("peak_start_hour", window.startHour)
            .add("peak_end_hour", window.endHour)
            .add("weekend_is_peak", window.weekendsArePeak)
            .add("rates", rates)
            .add("storage_backend", config.getStorageBackend())
            .add("data_file", options.get("data", config.getDataFile()));
        out_ << reply.str() << '\n';
        return 0;
    }

    if (command == "fare") {
        if (options.positional.size() < 3 || !isInteger(options.positional[1]) || !isInteger(options.positional[2])) {
            return usageError("Usage: fare <entry_unix_ts> <exit_unix_ts> [--type CAR|BIKE]");
        }
        const auto strategy = createFeeStrategy(config, vehicleType);
        const FeeBreakdown fee = strategy->calculateFee(timeutil::fromUnix(std::stoll(options.positional[1])),
                                                        timeutil::fromUnix(std::stoll(options.positional[2])));
        JsonObject reply = feeJson(fee);
        reply.add("ok", true).add("strategy", strategy->getName()).add("vehicle_type", vehicleType);
        out_ << reply.str() << '\n';
        return 0;
    }

    // Every command below works on the stored records.
    const auto repository = makeRepository(config, options);
    ParkingLot lot(config.getLotName(), config.buildSlots(), config);
    ParkingRecordManager manager(lot, *repository);
    manager.loadTransactions();

    if (command == "status") {
        lot.displayParkingStatus(out_);
        for (const auto& warning : repository->getWarnings()) {
            err_ << "warning: " << warning << '\n';
        }
        return 0;
    }

    const bool needsPlate = command == "entry" || command == "exit" || command == "cancel" || command == "active";
    std::string plate;
    if (needsPlate) {
        if (options.positional.size() < 2) {
            return usageError("Usage: " + command + " <plate>");
        }
        plate = Vehicle::normalizePlate(options.positional[1]);
        if (!Vehicle::isValidPlate(plate)) {
            throw ValidationException("'" + options.positional[1] +
                                      "' is not a valid number plate (4-15 letters/digits, e.g. MH12AB1234)");
        }
    }
    TimePoint at = timeutil::now();
    if (options.has("at")) {
        if (!isInteger(options.get("at"))) {
            return usageError("--at expects a UNIX timestamp in seconds");
        }
        at = timeutil::fromUnix(std::stoll(options.get("at")));
    }

    JsonObject reply;
    reply.add("ok", true);

    if (command == "slots") {
        JsonArray slots;
        for (const auto& slot : lot.getSlots()) {
            JsonObject json;
            json.add("slot_id", slot.getSlotId())
                .add("slot_number", slot.getSlotNumber())
                .add("slot_type", slot.getSlotType())
                .add("floor", slot.getFloor())
                .add("zone", std::string(1, slot.getZone()))
                .add("status", slot.getStatus())
                .add("number_plate", slot.getOccupantPlate());
            if (slot.getActiveTransactionId()) {
                json.add("session_id", *slot.getActiveTransactionId());
            } else {
                json.addNull("session_id");
            }
            slots.push(json);
        }
        JsonObject summary;
        summary.add("total", static_cast<int>(lot.getSlots().size()))
            .add("available", static_cast<int>(lot.getAvailableSlots().size()))
            .add("occupied", static_cast<int>(lot.getOccupiedSlots().size()));
        reply.add("slots", slots).add("summary", summary);
    } else if (command == "entry") {
        if (!isSupportedVehicleType(vehicleType)) {
            throw ValidationException("Unsupported vehicle type '" + vehicleType + "' (expected CAR or BIKE)");
        }
        const ParkingTransaction transaction = manager.checkIn(plate, vehicleType, at);
        reply.add("message", "Entry recorded. Slot: " + transaction.getSlotNumber())
            .add("transaction", transactionJson(transaction, lot));
    } else if (command == "exit") {
        const PaymentMethod method = parsePaymentMethod(options.get("method", "CASH"));
        const ParkingTransaction transaction = manager.checkOut(plate, at, method);
        const FeeBreakdown& fee = *transaction.getFee();
        reply.add("message", "Exit processed. Fare: Rs." + formatMoney(fee.totalAmount))
            .add("transaction", transactionJson(transaction, lot))
            .add("fare", feeJson(fee));
    } else if (command == "cancel") {
        const ParkingTransaction transaction = manager.cancel(plate, at);
        reply.add("message", "Session cancelled. Amount: 0").add("transaction", transactionJson(transaction, lot));
    } else if (command == "active") {
        const auto active = lot.findActiveTransaction(plate);
        reply.add("found", active.has_value());
        if (active) {
            reply.add("transaction", transactionJson(*active, lot));
        }
    } else if (command == "history") {
        int limit = 200;
        if (options.has("limit")) {
            if (!isInteger(options.get("limit")) || std::stoll(options.get("limit")) <= 0) {
                return usageError("--limit expects a positive whole number");
            }
            limit = static_cast<int>(std::min(std::stoll(options.get("limit")), 100000LL));
        }
        JsonArray transactions;
        int count = 0;
        for (const auto& transaction : manager.getParkingHistory(options.get("plate"))) {
            if (count++ >= limit) {
                break;
            }
            transactions.push(transactionJson(transaction, lot));
        }
        reply.add("transactions", transactions);
    } else {
        return usageError("Unknown command '" + command + "'");
    }

    JsonArray warnings;
    for (const auto& warning : repository->getWarnings()) {
        warnings.push(warning);
    }
    reply.add("storage", repository->describe()).add("warnings", warnings);
    out_ << reply.str() << '\n';
    return 0;
}

}  // namespace parking
