#include "storage/MySqlParkingRepository.hpp"

#include <mysql.h>

#include <cstdlib>
#include <cstring>
#include <deque>
#include <filesystem>
#include <memory>

#include "config/KeyValueFile.hpp"
#include "exceptions/ParkingException.hpp"
#include "models/ParkingTransaction.hpp"
#include "models/Vehicle.hpp"

namespace parking {

namespace {

void runQuery(MYSQL* connection, const char* sql) {
    if (mysql_query(connection, sql) != 0) {
        throw DatabaseException(std::string("Query failed (") + sql + "): " + mysql_error(connection));
    }
}

// RAII wrapper around MYSQL_STMT with typed parameter binding.
// Bound values are copied into deques, whose elements never move, so the
// pointers handed to the C API stay valid until execute().
class PreparedStatement {
public:
    PreparedStatement(MYSQL* connection, const std::string& sql) : statement_(mysql_stmt_init(connection)) {
        if (statement_ == nullptr) {
            throw DatabaseException("mysql_stmt_init failed: out of memory");
        }
        if (mysql_stmt_prepare(statement_, sql.c_str(), static_cast<unsigned long>(sql.size())) != 0) {
            const std::string error = mysql_stmt_error(statement_);
            mysql_stmt_close(statement_);
            throw DatabaseException("Could not prepare statement: " + error);
        }
        binds_.resize(mysql_stmt_param_count(statement_));
        std::memset(binds_.data(), 0, binds_.size() * sizeof(MYSQL_BIND));
    }
    ~PreparedStatement() { mysql_stmt_close(statement_); }

    PreparedStatement(const PreparedStatement&) = delete;
    PreparedStatement& operator=(const PreparedStatement&) = delete;

    PreparedStatement& bind(std::size_t index, const std::string& value) {
        std::string& stored = strings_.emplace_back(value);
        unsigned long& length = lengths_.emplace_back(static_cast<unsigned long>(stored.size()));
        MYSQL_BIND& b = slot(index);
        b.buffer_type = MYSQL_TYPE_STRING;
        b.buffer = stored.data();
        b.buffer_length = length;
        b.length = &length;
        return *this;
    }
    PreparedStatement& bind(std::size_t index, long long value) {
        MYSQL_BIND& b = slot(index);
        b.buffer_type = MYSQL_TYPE_LONGLONG;
        b.buffer = &integers_.emplace_back(value);
        return *this;
    }
    PreparedStatement& bind(std::size_t index, double value) {
        MYSQL_BIND& b = slot(index);
        b.buffer_type = MYSQL_TYPE_DOUBLE;
        b.buffer = &doubles_.emplace_back(value);
        return *this;
    }

    // Returns the number of affected rows.
    unsigned long long execute() {
        if (mysql_stmt_bind_param(statement_, binds_.data()) != 0 || mysql_stmt_execute(statement_) != 0) {
            throw DatabaseException(std::string("Statement failed: ") + mysql_stmt_error(statement_));
        }
        return mysql_stmt_affected_rows(statement_);
    }
    unsigned long long insertId() { return mysql_stmt_insert_id(statement_); }

private:
    MYSQL_BIND& slot(std::size_t index) {
        if (index >= binds_.size()) {
            throw DatabaseException("Parameter index " + std::to_string(index) + " out of range");
        }
        return binds_[index];
    }

    MYSQL_STMT* statement_;
    std::vector<MYSQL_BIND> binds_;
    std::deque<std::string> strings_;
    std::deque<unsigned long> lengths_;
    std::deque<long long> integers_;
    std::deque<double> doubles_;
};

// RAII SQL transaction: rolls back unless commit() was reached.
class SqlTransaction {
public:
    explicit SqlTransaction(MYSQL* connection) : connection_(connection) { runQuery(connection_, "START TRANSACTION"); }
    ~SqlTransaction() {
        if (!committed_) {
            mysql_query(connection_, "ROLLBACK");
        }
    }
    SqlTransaction(const SqlTransaction&) = delete;
    SqlTransaction& operator=(const SqlTransaction&) = delete;

    void commit() {
        runQuery(connection_, "COMMIT");
        committed_ = true;
    }

private:
    MYSQL* connection_;
    bool committed_ = false;
};

std::string column(MYSQL_ROW row, int index) { return row[index] ? row[index] : ""; }

std::optional<TimePoint> timeColumn(MYSQL_ROW row, int index) {
    if (row[index] == nullptr) {
        return std::nullopt;
    }
    return timeutil::fromUnix(std::atoll(row[index]));
}

std::string sessionPaymentStatus(const TransactionRecord& record) {
    if (record.status == "CANCELLED") return "WAIVED";
    if (record.paymentStatus == "SUCCESS") return "PAID";
    return "PENDING";
}

}  // namespace

MySqlSettings MySqlSettings::fromEnvironment(const std::string& envFile) {
    MySqlSettings settings;
    std::string port;
    const auto assign = [&settings, &port](const std::string& key, const std::string& value) {
        if (key == "DB_HOST") settings.host = value;
        else if (key == "DB_PORT") port = value;
        else if (key == "DB_NAME") settings.database = value;
        else if (key == "DB_USER") settings.user = value;
        else if (key == "DB_PASSWORD") settings.password = value;
    };
    std::error_code ec;
    if (std::filesystem::exists(envFile, ec)) {
        for (const auto& entry : readKeyValueFile(envFile)) {
            assign(entry.key, entry.value);
        }
    }
    for (const char* key : {"DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"}) {
        if (const char* value = std::getenv(key)) {
            assign(key, value);
        }
    }
    if (!port.empty()) {
        settings.port = static_cast<unsigned int>(std::strtoul(port.c_str(), nullptr, 10));
    }
    return settings;
}

MySqlParkingRepository::MySqlParkingRepository(const MySqlSettings& settings)
    : connection_(mysql_init(nullptr)),
      description_("MySQL database " + settings.database + " on " + settings.host + ":" + std::to_string(settings.port)) {
    if (connection_ == nullptr) {
        throw DatabaseException("mysql_init failed: out of memory");
    }
    unsigned int timeoutSeconds = 10;
    mysql_options(connection_, MYSQL_OPT_CONNECT_TIMEOUT, &timeoutSeconds);
    if (mysql_real_connect(connection_, settings.host.c_str(), settings.user.c_str(), settings.password.c_str(),
                           settings.database.c_str(), settings.port, nullptr, 0) == nullptr) {
        const std::string error = mysql_error(connection_);
        mysql_close(connection_);
        connection_ = nullptr;
        throw DatabaseException("Cannot connect to " + description_ + ": " + error);
    }
    mysql_set_character_set(connection_, "utf8mb4");
}

MySqlParkingRepository::~MySqlParkingRepository() {
    if (connection_ != nullptr) {
        mysql_close(connection_);
    }
}

std::string MySqlParkingRepository::describe() const { return description_; }

std::vector<TransactionRecord> MySqlParkingRepository::loadTransactions() {
    warnings_.clear();
    // No user input in this query, so a plain query is safe here.
    runQuery(connection_,
             "SELECT ps.session_id, v.number_plate, v.vehicle_type, sl.slot_number, ps.session_status, "
             "UNIX_TIMESTAMP(ps.entry_time), UNIX_TIMESTAMP(ps.exit_time), ps.base_minutes, ps.peak_minutes, "
             "ps.base_rate, ps.peak_rate, ps.base_amount, ps.peak_amount, ps.total_fare, "
             "py.payment_method, py.payment_status, UNIX_TIMESTAMP(py.payment_time) "
             "FROM parking_sessions ps "
             "JOIN vehicles v ON v.vehicle_id = ps.vehicle_id "
             "JOIN parking_slots sl ON sl.slot_id = ps.slot_id "
             "LEFT JOIN payments py ON py.session_id = ps.session_id "
             "ORDER BY ps.session_id");
    std::unique_ptr<MYSQL_RES, decltype(&mysql_free_result)> result(mysql_store_result(connection_),
                                                                    &mysql_free_result);
    if (!result) {
        throw DatabaseException(std::string("Could not read parking_sessions: ") + mysql_error(connection_));
    }

    std::vector<TransactionRecord> records;
    while (MYSQL_ROW row = mysql_fetch_row(result.get())) {
        TransactionRecord r;
        r.transactionId = std::atoi(row[0]);
        r.numberPlate = column(row, 1);
        r.vehicleType = column(row, 2);
        r.slotNumber = column(row, 3);
        r.status = column(row, 4);
        if (!isSupportedVehicleType(r.vehicleType)) {
            warnings_.push_back("session #" + std::to_string(r.transactionId) + " skipped: vehicle type " +
                                r.vehicleType + " is not modelled in the C++ core");
            continue;
        }
        r.entryTime = timeColumn(row, 5).value_or(TimePoint{});
        r.exitTime = timeColumn(row, 6);
        if (r.status != "ACTIVE") {
            FeeBreakdown fee;
            fee.baseMinutes = std::atoll(column(row, 7).c_str());
            fee.peakMinutes = std::atoll(column(row, 8).c_str());
            fee.baseRate = std::atof(column(row, 9).c_str());
            fee.peakRate = std::atof(column(row, 10).c_str());
            fee.baseAmount = std::atof(column(row, 11).c_str());
            fee.peakAmount = std::atof(column(row, 12).c_str());
            fee.totalAmount = std::atof(column(row, 13).c_str());
            fee.totalMinutes = r.exitTime ? (*r.exitTime - r.entryTime).count() : 0;
            r.fee = fee;
        }
        const std::string method = column(row, 14);
        if (r.status == "COMPLETED" && (method == "CASH" || method == "UPI" || method == "CARD")) {
            r.paymentMethod = method;
            r.paymentStatus = column(row, 15) == "SUCCESS" ? "SUCCESS" : "PENDING";
            r.paymentTime = timeColumn(row, 16);
        }
        records.push_back(r);
    }
    return records;
}

void MySqlParkingRepository::saveTransaction(const TransactionRecord& record) {
    if (record.status == "ACTIVE") {
        insertActiveSession(record);
    } else {
        finishSession(record);
    }
}

void MySqlParkingRepository::insertActiveSession(const TransactionRecord& record) {
    SqlTransaction transaction(connection_);

    PreparedStatement upsertVehicle(connection_,
                                    "INSERT INTO vehicles (number_plate, vehicle_type) VALUES (?, ?) "
                                    "ON DUPLICATE KEY UPDATE vehicle_id = LAST_INSERT_ID(vehicle_id), updated_at = NOW()");
    upsertVehicle.bind(0, record.numberPlate).bind(1, record.vehicleType).execute();
    const long long vehicleId = static_cast<long long>(upsertVehicle.insertId());

    // Atomic check-and-claim: fails if another process took the slot first.
    // LAST_INSERT_ID(slot_id) hands the claimed slot's id back via insertId().
    PreparedStatement claimSlot(connection_,
                                "UPDATE parking_slots SET status = 'OCCUPIED', slot_id = LAST_INSERT_ID(slot_id) "
                                "WHERE slot_number = ? AND status = 'AVAILABLE'");
    if (claimSlot.bind(0, record.slotNumber).execute() != 1) {
        throw SlotUnavailableException("Slot " + record.slotNumber + " is not available in the database");
    }
    const long long slotId = static_cast<long long>(claimSlot.insertId());

    // Plain VALUES (not INSERT ... SELECT FROM parking_slots): the schema's
    // trg_slot_occupied_on_entry trigger updates parking_slots, and MySQL
    // forbids a trigger from updating a table the statement is reading.
    PreparedStatement insertSession(connection_,
                                    "INSERT INTO parking_sessions (session_id, vehicle_id, slot_id, entry_time, session_status) "
                                    "VALUES (?, ?, ?, FROM_UNIXTIME(?), 'ACTIVE')");
    insertSession.bind(0, static_cast<long long>(record.transactionId))
        .bind(1, vehicleId)
        .bind(2, slotId)
        .bind(3, timeutil::toUnix(record.entryTime))
        .execute();

    transaction.commit();
}

void MySqlParkingRepository::finishSession(const TransactionRecord& record) {
    if (!record.exitTime || !record.fee) {
        throw ValidationException("A finished session needs an exit time and a fee");
    }
    SqlTransaction transaction(connection_);
    const FeeBreakdown& fee = *record.fee;

    PreparedStatement update(connection_,
                             "UPDATE parking_sessions SET exit_time = FROM_UNIXTIME(?), duration_seconds = ?, "
                             "base_minutes = ?, peak_minutes = ?, base_rate = ?, peak_rate = ?, base_amount = ?, "
                             "peak_amount = ?, total_fare = ?, is_rush_hour = ?, session_status = ?, "
                             "payment_status = ?, updated_at = NOW() "
                             "WHERE session_id = ? AND session_status = 'ACTIVE'");
    update.bind(0, timeutil::toUnix(*record.exitTime))
        .bind(1, static_cast<long long>((*record.exitTime - record.entryTime).count()))
        .bind(2, fee.baseMinutes)
        .bind(3, fee.peakMinutes)
        .bind(4, fee.baseRate)
        .bind(5, fee.peakRate)
        .bind(6, fee.baseAmount)
        .bind(7, fee.peakAmount)
        .bind(8, fee.totalAmount)
        .bind(9, static_cast<long long>(fee.isRushHour() ? 1 : 0))
        .bind(10, record.status)
        .bind(11, sessionPaymentStatus(record))
        .bind(12, static_cast<long long>(record.transactionId));
    if (update.execute() != 1) {
        throw InvalidSessionStateException("Session #" + std::to_string(record.transactionId) +
                                           " is not ACTIVE in the database");
    }

    if (!record.paymentMethod.empty() && record.paymentStatus == "SUCCESS") {
        PreparedStatement payment(connection_,
                                  "INSERT INTO payments (session_id, amount, payment_method, payment_status, payment_time) "
                                  "VALUES (?, ?, ?, 'SUCCESS', FROM_UNIXTIME(?))");
        payment.bind(0, static_cast<long long>(record.transactionId))
            .bind(1, fee.totalAmount)
            .bind(2, record.paymentMethod)
            .bind(3, timeutil::toUnix(record.paymentTime.value_or(*record.exitTime)))
            .execute();
    }
    transaction.commit();
}

}  // namespace parking
