#pragma once

#include <iosfwd>
#include <string>

namespace parking {

// `parkinglot demo`: a short, reproducible walk-through of the OOP concepts
// for the viva. It drives the real application classes (ParkingLot,
// ParkingRecordManager, CsvParkingRepository, fee strategies ...) against a
// temporary CSV file - nothing here re-implements their logic.
class DemoRunner {
public:
    explicit DemoRunner(std::ostream& out);
    void run();

private:
    void section(int number, const std::string& title);

    std::ostream& out_;
};

}  // namespace parking
