#include "app/DemoRunner.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <memory>
#include <ostream>
#include <vector>

#include "config/AppConfig.hpp"
#include "exceptions/ParkingException.hpp"
#include "services/ParkingFeeStrategy.hpp"
#include "services/ParkingLot.hpp"
#include "services/ParkingRecordManager.hpp"
#include "storage/CsvParkingRepository.hpp"
#include "util/Validation.hpp"

namespace fs = std::filesystem;

namespace parking {

namespace {

std::vector<ParkingSlot> demoSlots() {
    return {ParkingSlot(1, "1", 'A', 1, "STANDARD"), ParkingSlot(2, "2", 'A', 1, "STANDARD"),
            ParkingSlot(3, "3", 'A', 1, "COMPACT")};
}

}  // namespace

DemoRunner::DemoRunner(std::ostream& out) : out_(out) {}

void DemoRunner::section(int number, const std::string& title) {
    out_ << "\n=== " << number << ". " << title << " ===\n";
}

void DemoRunner::run() {
    out_ << std::fixed << std::setprecision(2);
    out_ << "Smart Parking - C++ OOP demonstration\n"
         << "(Billing rule kept from parkinglot.c: each real second is billed as one minute.)\n";

    const AppConfig config = AppConfig::defaults();
    const fs::path csvPath = fs::temp_directory_path() / "parkinglot_oop_demo.csv";
    std::error_code ec;
    fs::remove(csvPath, ec);

    // 1 + 7. Objects of derived classes, used through base-class pointers.
    section(1, "Classes & objects: creating vehicles");
    ParkingLot lot("Demo Lot", demoSlots(), config);
    const auto car = lot.registerVehicle("MH12AB1234", "CAR");
    const auto bike = lot.registerVehicle("mh 01 ef 9012", "BIKE");  // normalised by Vehicle
    const std::vector<std::shared_ptr<const Vehicle>> vehicles = {car, bike};
    for (const auto& vehicle : vehicles) {
        out_ << "  ";
        vehicle->displayDetails(out_);  // virtual call: FourWheeler / TwoWheeler version
        out_ << '\n';
    }

    // 2. Slot allocation through ParkingLot (std::find_if over std::vector<ParkingSlot>).
    section(2, "Parking-slot allocation");
    CsvParkingRepository repository(csvPath.string());
    ParkingRecordManager manager(lot, repository);
    const TimePoint carEntry = timeutil::makeLocal(2026, 10, 21, 17, 59, 0);  // a Wednesday
    const TimePoint bikeEntry = carEntry + std::chrono::seconds(30);
    const ParkingTransaction carIn = manager.checkIn(car->getNumberPlate(), car->getVehicleType(), carEntry);
    const ParkingTransaction bikeIn = manager.checkIn(bike->getNumberPlate(), bike->getVehicleType(), bikeEntry);
    out_ << "  " << car->getNumberPlate() << " -> slot " << carIn.getSlotNumber() << '\n'
         << "  " << bike->getNumberPlate() << " -> slot " << bikeIn.getSlotNumber() << '\n';
    lot.displayParkingStatus(out_);

    // 3 + 4. Exit, duration and fee.
    section(3, "Entry and exit time recording");
    const TimePoint carExit = timeutil::makeLocal(2026, 10, 21, 18, 1, 0);
    const ParkingTransaction carOut = manager.checkOut(car->getNumberPlate(), carExit, PaymentMethod::Cash);
    carOut.displayTransaction(out_);
    out_ << '\n';

    section(4, "Parking-fee calculation (peak window 18:00-22:00)");
    out_ << "  The car stayed 17:59:00-18:01:00: 60 s before 18:00 at the base rate,\n"
         << "  60 s after 18:00 at the peak rate.\n";
    const auto& carFee = *carOut.getFee();
    out_ << "  base " << carFee.baseMinutes << " x Rs " << carFee.baseRate << " = Rs " << carFee.baseAmount
         << "\n  peak " << carFee.peakMinutes << " x Rs " << carFee.peakRate << " = Rs " << carFee.peakAmount
         << "\n  total Rs " << carFee.totalAmount << '\n';
    const ParkingTransaction bikeOut =
        manager.checkOut(bike->getNumberPlate(), bikeEntry + std::chrono::seconds(60), PaymentMethod::Upi);
    out_ << "  Bike (own BIKE rate card): Rs " << bikeOut.getFee()->totalAmount << '\n';

    section(5, "Slot release after exit");
    lot.displayParkingStatus(out_);
    out_ << "  Available slots: " << lot.getAvailableSlots().size() << " of " << lot.getSlots().size() << '\n';

    // 6. File handling: a brand-new lot + repository reads the same CSV back.
    section(6, "Saving and loading parking records (CSV file handling)");
    out_ << "  Records written to " << csvPath.string() << ":\n";
    {
        std::ifstream in(csvPath);
        std::string line;
        while (std::getline(in, line)) {
            out_ << "    " << line << '\n';
        }
    }
    CsvParkingRepository reloadedRepository(csvPath.string());
    ParkingLot reloadedLot("Demo Lot (reloaded)", demoSlots(), config);
    ParkingRecordManager reloadedManager(reloadedLot, reloadedRepository);
    out_ << "  Reloaded " << reloadedManager.loadTransactions() << " transactions. Transaction #1:\n  ";
    if (const auto found = reloadedManager.findTransactionById(1)) {
        found->displayTransaction(out_);
        out_ << '\n';
    }

    section(7, "Inheritance: vehicle categories");
    for (const auto& vehicle : vehicles) {
        const Vehicle& base = *vehicle;  // used through a base-class reference
        out_ << "  " << base.getNumberPlate() << ": " << base.getCategoryName() << ", " << base.getWheelCount()
             << " wheels, tariff = " << lot.strategyFor(base.getVehicleType()).describe() << '\n';
    }

    // 8. Same call, different behaviour, chosen at runtime.
    section(8, "Runtime polymorphism: fee strategies");
    std::vector<std::unique_ptr<ParkingFeeStrategy>> strategies;
    strategies.push_back(std::make_unique<PeakHourFeeStrategy>(config.rateFor("CAR"), config.getPeakWindow()));
    strategies.push_back(std::make_unique<PeakHourFeeStrategy>(config.rateFor("BIKE"), config.getPeakWindow()));
    strategies.push_back(std::make_unique<FlatRateFeeStrategy>(config.getFlatRatePerMinute()));
    const TimePoint saturday = timeutil::makeLocal(2026, 10, 24, 10, 0, 0);
    for (const auto& strategy : strategies) {
        const ParkingFeeStrategy& base = *strategy;
        out_ << "  " << std::left << std::setw(10) << base.getName() << std::right << " [" << base.describe() << "]\n"
             << "      weekday 17:59-18:01 -> Rs " << base.calculateFee(carEntry, carExit).totalAmount
             << "   saturday 10:00-10:02 -> Rs "
             << base.calculateFee(saturday, saturday + std::chrono::seconds(120)).totalAmount << '\n';
    }

    section(9, "Exception handling");
    const TimePoint later = carExit + std::chrono::hours(1);
    for (const char* plate : {"MH14CD5678", "MH04IJ7890", "MH06KL2345", "DL01OP1234"}) {
        try {
            const auto transaction = manager.checkIn(plate, "CAR", later);
            out_ << "  " << plate << " parked in slot " << transaction.getSlotNumber() << '\n';
        } catch (const SlotUnavailableException& e) {
            out_ << "  caught SlotUnavailableException [" << e.code() << "]: " << e.what() << '\n';
        }
    }
    try {
        ParkingTransaction alreadyClosed = carOut;
        alreadyClosed.endSession(later, lot.strategyFor("CAR"));
    } catch (const InvalidSessionStateException& e) {
        out_ << "  caught InvalidSessionStateException [" << e.code() << "]: " << e.what() << '\n';
    }
    try {
        manager.checkOut("MH14CD5678", later - std::chrono::seconds(10), PaymentMethod::Cash);
    } catch (const ParkingException& e) {  // caught through the base class
        out_ << "  caught " << e.code() << ": " << e.what() << '\n';
    }
    try {
        lot.registerVehicle("??", "CAR");
    } catch (const ValidationException& e) {
        out_ << "  caught ValidationException [" << e.code() << "]: " << e.what() << '\n';
    }
    try {
        AppConfig::loadFromFile("missing-config.cfg");
    } catch (const StorageException& e) {
        out_ << "  caught StorageException [" << e.code() << "]: " << e.what() << '\n';
    }

    section(10, "STL containers and custom templates");
    out_ << "  std::vector<ParkingSlot>, std::unordered_map<std::string, ...> indexes, std::optional,\n"
         << "  std::unique_ptr<ParkingFeeStrategy>, std::shared_ptr<const Vehicle>, std::chrono, std::find_if.\n";
    const RateCard* bikeRates = findOrNull(config.getRateCards(), std::string("BIKE"));
    const RateCard* truckRates = findOrNull(config.getRateCards(), std::string("TRUCK"));
    out_ << "  findOrNull(rateCards, \"BIKE\")  -> ";
    if (bikeRates) {
        out_ << "found, base Rs " << bikeRates->baseRate << "/min\n";
    } else {
        out_ << "nullptr\n";
    }
    out_ << "  findOrNull(rateCards, \"TRUCK\") -> " << (truckRates ? "found" : "nullptr") << '\n';
    out_ << "  requireInRange(19, 0, 23, \"hour\") -> " << requireInRange(19, 0, 23, "hour") << '\n';
    try {
        requireInRange(2.5, 0.0, 1.0, std::string("discount"));
    } catch (const ValidationException& e) {
        out_ << "  requireInRange(2.5, 0.0, 1.0, \"discount\") -> ValidationException: " << e.what() << '\n';
    }

    fs::remove(csvPath, ec);
    out_ << "\nDemo finished (temporary CSV removed).\n";
}

}  // namespace parking
