#pragma once

#include <string>
#include <vector>

#include "storage/ParkingRepository.hpp"

namespace parking {

// Stores transactions in parking_data.csv.
//
// Compatibility with the original file (main branch):
//   * the first four columns are unchanged: Number Plate, Entry Time,
//     Exit Time, Slot (times as dd/mm/YYYY HH:MM:SS);
//   * extra columns (id, type, status, fee, payment) are appended after them;
//   * a legacy 4-column file is read as-is, and a one-time copy is kept as
//     <file>.legacy-backup before it is first rewritten in the new layout.
//
// Safety:
//   * a missing file is an empty history (it is created on the first save);
//   * malformed rows are reported as warnings and written back verbatim at
//     the end of the file, never silently dropped;
//   * every save writes <file>.tmp completely, then renames it over the real
//     file, so a crash mid-write cannot leave a half-written CSV.
class CsvParkingRepository : public ParkingRepository {
public:
    explicit CsvParkingRepository(std::string path);

    std::vector<TransactionRecord> loadTransactions() override;
    void saveTransaction(const TransactionRecord& record) override;
    std::string describe() const override { return "CSV file " + path_; }
    std::vector<std::string> getWarnings() const override { return warnings_; }

    const std::string& getPath() const { return path_; }

private:
    void readFile();
    void writeFile();

    std::string path_;
    bool loaded_ = false;
    bool legacyFormat_ = false;
    std::vector<TransactionRecord> records_;
    std::vector<std::string> preservedLines_;  // malformed rows, kept verbatim
    std::vector<std::string> warnings_;
};

}  // namespace parking
