// CSV file handling, restart persistence and the JSON command interface.

#include <filesystem>
#include <fstream>
#include <sstream>

#include "TestFramework.hpp"
#include "app/CommandLineApp.hpp"
#include "config/AppConfig.hpp"
#include "exceptions/ParkingException.hpp"
#include "services/ParkingLot.hpp"
#include "services/ParkingRecordManager.hpp"
#include "storage/CsvParkingRepository.hpp"

using namespace parking;

namespace {

using std::chrono::seconds;

const TimePoint kEntry = timeutil::makeLocal(2026, 10, 21, 17, 59, 0);

std::string readAll(const std::string& path) {
    std::ifstream in(path);
    std::ostringstream content;
    content << in.rdbuf();
    return content.str();
}

void writeAll(const std::string& path, const std::string& content) {
    std::ofstream out(path);
    out << content;
}

ParkingLot defaultLot() {
    const AppConfig config = AppConfig::defaults();
    return ParkingLot(config.getLotName(), config.buildSlots(), config);
}

std::string runCli(const std::vector<std::string>& args, int* exitCode = nullptr) {
    std::ostringstream out, err;
    CommandLineApp app(out, err);
    const int code = app.run(args);
    if (exitCode) *exitCode = code;
    return out.str();
}

}  // namespace

// --- 7. CSV save and load ---------------------------------------------------------

TEST_CASE(csv_records_round_trip_through_save_and_load) {
    testing::TempDir dir;
    const std::string path = dir.file("parking_data.csv");
    {
        ParkingLot lot = defaultLot();
        CsvParkingRepository repository(path);
        ParkingRecordManager manager(lot, repository);
        manager.loadTransactions();
        manager.checkIn("MH12AB1234", "CAR", kEntry);
        manager.checkIn("MH01EF9012", "BIKE", kEntry + seconds(5));
        manager.checkOut("MH12AB1234", kEntry + seconds(120), PaymentMethod::Upi);
    }

    // A new process: fresh lot, fresh repository, same file.
    ParkingLot lot = defaultLot();
    CsvParkingRepository repository(path);
    ParkingRecordManager manager(lot, repository);
    CHECK_EQ(manager.loadTransactions(), std::size_t(2));
    CHECK(repository.getWarnings().empty());

    const auto completed = manager.findTransactionById(1);
    CHECK(completed.has_value());
    CHECK(completed->getStatus() == TransactionStatus::Completed);
    CHECK_EQ(completed->getFee()->baseMinutes, 60LL);
    CHECK_EQ(completed->getFee()->peakMinutes, 60LL);
    CHECK_NEAR(completed->getFee()->totalAmount, 88.20);
    CHECK(completed->getPayment()->getPaymentMethod() == PaymentMethod::Upi);
    CHECK_EQ(completed->calculateDuration(), 120LL);

    // The still-active bike keeps its slot after the "restart".
    const auto active = lot.findActiveTransaction("MH01EF9012");
    CHECK(active.has_value());
    CHECK_EQ(active->getVehicle().getVehicleType(), std::string("BIKE"));
    CHECK(!lot.findSlot("2")->isAvailable());
    CHECK(lot.findSlot("1")->isAvailable());
    CHECK_EQ(manager.checkIn("MH14CD5678", "CAR", kEntry + seconds(200)).getTransactionId(), 3);

    // The first four columns keep the original layout.
    CHECK(readAll(path).find("Number Plate,Entry Time,Exit Time,Slot,") == 0);
    CHECK(readAll(path).find("MH12AB1234,21/10/2026 17:59:00,21/10/2026 18:01:00,1,1,CAR,COMPLETED") !=
          std::string::npos);
    CHECK(!std::filesystem::exists(path + ".tmp"));
}

// --- 8. Missing and malformed files ---------------------------------------------------

TEST_CASE(missing_csv_file_means_empty_history_and_is_created_on_save) {
    testing::TempDir dir;
    const std::string path = dir.file("new.csv");
    CsvParkingRepository repository(path);
    CHECK(repository.loadTransactions().empty());
    CHECK(!std::filesystem::exists(path));

    ParkingLot lot = defaultLot();
    ParkingRecordManager manager(lot, repository);
    manager.checkIn("MH12AB1234", "CAR", kEntry);
    CHECK(std::filesystem::exists(path));
}

TEST_CASE(malformed_rows_are_reported_and_kept_not_discarded) {
    testing::TempDir dir;
    const std::string path = dir.file("data.csv");
    CsvParkingRepository seed(path);
    ParkingLot seedLot = defaultLot();
    ParkingRecordManager seedManager(seedLot, seed);
    seedManager.checkIn("MH12AB1234", "CAR", kEntry);

    std::ofstream(path, std::ios::app) << "GARBAGE,not a date,,1\n"
                                       << "MH14CD5678,32/13/2026 10:00:00,,2,2,CAR,ACTIVE,,,,,,,,,,\n";

    CsvParkingRepository repository(path);
    ParkingLot lot = defaultLot();
    ParkingRecordManager manager(lot, repository);
    CHECK_EQ(manager.loadTransactions(), std::size_t(1));
    CHECK_EQ(repository.getWarnings().size(), std::size_t(2));

    manager.checkIn("MH04IJ7890", "CAR", kEntry + seconds(10));  // forces a rewrite
    const std::string content = readAll(path);
    CHECK(content.find("GARBAGE,not a date,,1") != std::string::npos);
    CHECK(content.find("32/13/2026 10:00:00") != std::string::npos);
    CHECK(content.find("MH04IJ7890") != std::string::npos);
}

TEST_CASE(unrecognised_csv_header_is_refused_and_left_untouched) {
    testing::TempDir dir;
    const std::string path = dir.file("other.csv");
    writeAll(path, "name,score\nalice,10\n");
    CsvParkingRepository repository(path);
    CHECK_THROWS_AS(repository.loadTransactions(), StorageException);

    TransactionRecord record;
    record.transactionId = 1;
    record.numberPlate = "MH12AB1234";
    record.slotNumber = "1";
    record.status = "ACTIVE";
    record.entryTime = kEntry;
    CHECK_THROWS_AS(repository.saveTransaction(record), StorageException);
    CHECK_EQ(readAll(path), std::string("name,score\nalice,10\n"));
}

TEST_CASE(legacy_four_column_csv_is_loaded_and_backed_up_before_upgrade) {
    testing::TempDir dir;
    const std::string path = dir.file("parking_data.csv");
    // Same layout (and BOM-free header) as the original pandas-based app.
    const std::string legacy =
        "Number Plate,Entry Time,Exit Time,Slot\n"
        "MH12AB3456,17/04/2026 20:59:12,17/04/2026 21:09:53,1\n"
        "TH09BY9720,17/04/2026 21:03:21,,3\n";
    writeAll(path, legacy);

    ParkingLot lot = defaultLot();
    CsvParkingRepository repository(path);
    ParkingRecordManager manager(lot, repository);
    CHECK_EQ(manager.loadTransactions(), std::size_t(2));
    CHECK(manager.findTransactionById(1)->getStatus() == TransactionStatus::Completed);
    CHECK(!manager.findTransactionById(1)->getFee().has_value());  // the old app never stored fees
    CHECK(lot.findActiveTransaction("TH09BY9720").has_value());
    CHECK(!lot.findSlot("3")->isAvailable());

    manager.checkOut("TH09BY9720", timeutil::makeLocal(2026, 4, 17, 21, 5, 0), PaymentMethod::Cash);
    CHECK_EQ(readAll(path + ".legacy-backup"), legacy);
    CHECK(readAll(path).find("Transaction ID") != std::string::npos);
    CHECK(readAll(path).find("MH12AB3456,17/04/2026 20:59:12,17/04/2026 21:09:53,1,1,CAR,COMPLETED") !=
          std::string::npos);
}

TEST_CASE(inconsistent_records_fail_loading_with_a_clear_message) {
    testing::TempDir dir;
    const std::string path = dir.file("clash.csv");
    writeAll(path,
             "Number Plate,Entry Time,Exit Time,Slot\n"
             "MH12AB3456,17/04/2026 20:59:12,,1\n"
             "HR98AA7777,17/04/2026 20:59:22,,1\n");
    ParkingLot lot = defaultLot();
    CsvParkingRepository repository(path);
    ParkingRecordManager manager(lot, repository);
    try {
        manager.loadTransactions();
        CHECK(false);
    } catch (const StorageException& e) {
        CHECK(std::string(e.what()).find("HR98AA7777") != std::string::npos);
    }
}

// --- JSON commands used by Python -------------------------------------------------------

TEST_CASE(json_cli_entry_exit_and_errors) {
    testing::TempDir dir;
    const std::string data = dir.file("cli.csv");
    const std::string entryTs = std::to_string(timeutil::toUnix(kEntry));
    const std::string exitTs = std::to_string(timeutil::toUnix(kEntry) + 120);
    int code = -1;

    std::string reply = runCli({"entry", "mh12ab1234", "--data", data, "--at", entryTs}, &code);
    CHECK_EQ(code, 0);
    CHECK(reply.find("\"ok\":true") != std::string::npos);
    CHECK(reply.find("\"slot_number\":\"1\"") != std::string::npos);
    CHECK(reply.find("\"zone\":\"A\"") != std::string::npos);

    reply = runCli({"entry", "MH12AB1234", "--data", data}, &code);
    CHECK_EQ(code, 1);
    CHECK(reply.find("\"error_code\":\"ALREADY_PARKED\"") != std::string::npos);

    reply = runCli({"active", "MH12AB1234", "--data", data}, &code);
    CHECK(reply.find("\"found\":true") != std::string::npos);

    reply = runCli({"exit", "MH12AB1234", "--data", data, "--at", exitTs, "--method", "UPI"}, &code);
    CHECK_EQ(code, 0);
    CHECK(reply.find("\"total_amount\":88.20") != std::string::npos);
    CHECK(reply.find("\"payment_status\":\"PAID\"") != std::string::npos);

    reply = runCli({"exit", "MH12AB1234", "--data", data}, &code);
    CHECK_EQ(code, 1);
    CHECK(reply.find("\"error_code\":\"NOT_FOUND\"") != std::string::npos);

    reply = runCli({"entry", "!!", "--data", data}, &code);
    CHECK(reply.find("\"error_code\":\"VALIDATION_ERROR\"") != std::string::npos);

    reply = runCli({"slots", "--data", data}, &code);
    CHECK(reply.find("\"total\":30,\"available\":30,\"occupied\":0") != std::string::npos);

    reply = runCli({"history", "--data", data}, &code);
    CHECK(reply.find("\"session_status\":\"COMPLETED\"") != std::string::npos);

    reply = runCli({"slots", "--data", data, "--config", dir.file("nope.cfg")}, &code);
    CHECK_EQ(code, 1);
    CHECK(reply.find("\"error_code\":\"STORAGE_ERROR\"") != std::string::npos);

    reply = runCli({"frobnicate"}, &code);
    CHECK_EQ(code, 1);
    CHECK(reply.find("USAGE_ERROR") != std::string::npos);
}
