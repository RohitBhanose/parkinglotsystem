#pragma once

// Optional MySQL backend. Only compiled when CMake is configured with
// -DPARKING_WITH_MYSQL=ON (needs the MySQL C client library, libmysql).

#include <string>
#include <vector>

#include "storage/ParkingRepository.hpp"

struct MYSQL;  // from <mysql.h>; kept out of this header on purpose

namespace parking {

struct MySqlSettings {
    std::string host = "localhost";
    unsigned int port = 3306;
    std::string user = "root";
    std::string password;
    std::string database = "ParkingLot";

    // Reads DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD - the same names
    // db.py uses. Real environment variables win over the .env file.
    static MySqlSettings fromEnvironment(const std::string& envFile = ".env");
};

// Stores transactions in the existing ParkingLot schema (database/schema.sql):
// vehicles, parking_slots, parking_sessions, payments.
//
//   * every statement that carries a value is a prepared statement - user
//     input is never concatenated into SQL;
//   * each save runs inside one SQL transaction (RAII guard rolls back on error);
//   * a new session first claims its slot with
//       UPDATE parking_slots SET status='OCCUPIED' WHERE slot_number=? AND status='AVAILABLE'
//     so two processes can never be given the same slot;
//   * the schema's triggers still run (duplicate-entry guard, slot release).
//
// Rows whose vehicle type the C++ model does not cover (TRUCK, OTHER) are
// skipped with a warning instead of failing the whole load.
class MySqlParkingRepository : public ParkingRepository {
public:
    explicit MySqlParkingRepository(const MySqlSettings& settings);
    ~MySqlParkingRepository() override;

    MySqlParkingRepository(const MySqlParkingRepository&) = delete;
    MySqlParkingRepository& operator=(const MySqlParkingRepository&) = delete;

    std::vector<TransactionRecord> loadTransactions() override;
    void saveTransaction(const TransactionRecord& record) override;
    std::string describe() const override;
    std::vector<std::string> getWarnings() const override { return warnings_; }

private:
    void insertActiveSession(const TransactionRecord& record);
    void finishSession(const TransactionRecord& record);

    MYSQL* connection_ = nullptr;
    std::string description_;
    std::vector<std::string> warnings_;
};

}  // namespace parking
