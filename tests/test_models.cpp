// Vehicles, slots, transactions, payments and the ParkingLot rules.

#include <map>
#include <sstream>

#include "TestFramework.hpp"
#include "config/AppConfig.hpp"
#include "exceptions/ParkingException.hpp"
#include "models/ParkingSlot.hpp"
#include "models/ParkingTransaction.hpp"
#include "models/Vehicle.hpp"
#include "services/ParkingLot.hpp"
#include "util/Validation.hpp"

using namespace parking;

namespace {

ParkingLot smallLot(int slotCount = 2) {
    std::vector<ParkingSlot> slots;
    for (int i = 1; i <= slotCount; ++i) {
        slots.emplace_back(i, std::to_string(i), 'A', 1, "STANDARD");
    }
    return ParkingLot("Test Lot", std::move(slots), AppConfig::defaults());
}

const TimePoint kWednesday1000 = timeutil::makeLocal(2026, 10, 21, 10, 0, 0);

}  // namespace

// --- 9. Derived vehicle classes -------------------------------------------

TEST_CASE(derived_vehicle_classes_share_base_data_and_specialise) {
    TwoWheeler bike(1, "MH01EF9012");
    FourWheeler car(2, "MH12AB1234");
    const Vehicle& bikeBase = bike;
    const Vehicle& carBase = car;

    CHECK_EQ(bikeBase.getVehicleType(), std::string("BIKE"));
    CHECK_EQ(carBase.getVehicleType(), std::string("CAR"));
    CHECK_EQ(bikeBase.getWheelCount(), 2);
    CHECK_EQ(carBase.getWheelCount(), 4);
    CHECK_EQ(bikeBase.getVehicleId(), 1);

    std::ostringstream details;
    bikeBase.displayDetails(details);  // virtual: TwoWheeler override
    CHECK(details.str().find("two-wheeler") != std::string::npos);
}

TEST_CASE(vehicle_factory_and_plate_validation) {
    CHECK_EQ(createVehicle(1, "MH12AB1234", "BIKE")->getWheelCount(), 2);
    CHECK_EQ(createVehicle(1, "MH12AB1234", "CAR")->getWheelCount(), 4);
    CHECK_THROWS_AS(createVehicle(1, "MH12AB1234", "TRUCK"), ValidationException);
    CHECK_THROWS_AS(FourWheeler(1, "??"), ValidationException);
    CHECK_THROWS_AS(FourWheeler(0, "MH12AB1234"), ValidationException);

    CHECK_EQ(Vehicle::normalizePlate(" mh 12-ab.1234 "), std::string("MH12AB1234"));
    CHECK_EQ(FourWheeler(1, "mh12ab1234").getNumberPlate(), std::string("MH12AB1234"));
    CHECK(Vehicle::isValidPlate("22BH6517A"));
    CHECK(!Vehicle::isValidPlate("ABCD"));    // no digit
    CHECK(!Vehicle::isValidPlate("MH1"));     // too short
    CHECK(!Vehicle::isValidPlate("MH12;DROP"));
}

// --- 1-3. Slot allocation and release ----------------------------------------

TEST_CASE(vehicle_is_assigned_to_first_available_slot) {
    ParkingLot lot = smallLot(3);
    const auto first = lot.parkVehicle(lot.registerVehicle("MH12AB1234", "CAR"), kWednesday1000);
    const auto second = lot.parkVehicle(lot.registerVehicle("MH14CD5678", "CAR"), kWednesday1000);
    CHECK_EQ(first.getSlotNumber(), std::string("1"));
    CHECK_EQ(second.getSlotNumber(), std::string("2"));
    CHECK(!lot.findSlot("1")->isAvailable());
    CHECK_EQ(lot.findSlot("1")->getOccupantPlate(), std::string("MH12AB1234"));
    CHECK_EQ(lot.getAvailableSlots().size(), std::size_t(1));
    CHECK_EQ(lot.getOccupiedSlots().size(), std::size_t(2));
}

TEST_CASE(occupied_slot_cannot_take_another_vehicle) {
    ParkingSlot slot(1, "1", 'A', 1, "STANDARD");
    slot.assignVehicle(10, "MH12AB1234");
    CHECK_THROWS_AS(slot.assignVehicle(11, "MH14CD5678"), SlotUnavailableException);
    CHECK_EQ(slot.getOccupantPlate(), std::string("MH12AB1234"));
    CHECK_THROWS_AS(slot.releaseVehicle(11), InvalidSessionStateException);  // wrong session

    ParkingLot lot = smallLot(1);
    lot.parkVehicle(lot.registerVehicle("MH12AB1234", "CAR"), kWednesday1000);
    CHECK_THROWS_AS(lot.parkVehicle(lot.registerVehicle("MH14CD5678", "CAR"), kWednesday1000),
                    SlotUnavailableException);
}

TEST_CASE(vehicle_cannot_have_two_active_sessions) {
    ParkingLot lot = smallLot(2);
    const auto car = lot.registerVehicle("MH12AB1234", "CAR");
    lot.parkVehicle(car, kWednesday1000);
    try {
        lot.parkVehicle(car, kWednesday1000);
        CHECK(false);
    } catch (const InvalidSessionStateException& e) {
        CHECK_EQ(e.code(), std::string("ALREADY_PARKED"));
    }
    CHECK_EQ(lot.getOccupiedSlots().size(), std::size_t(1));
}

TEST_CASE(slot_becomes_available_after_valid_exit) {
    ParkingLot lot = smallLot(1);
    lot.parkVehicle(lot.registerVehicle("MH12AB1234", "CAR"), kWednesday1000);
    const auto done = lot.removeVehicle("MH12AB1234", kWednesday1000 + std::chrono::seconds(90), PaymentMethod::Cash);
    CHECK(done.getStatus() == TransactionStatus::Completed);
    CHECK(lot.findSlot("1")->isAvailable());
    CHECK(!lot.findActiveTransaction("MH12AB1234").has_value());
    // The freed slot can be used again.
    CHECK_EQ(lot.parkVehicle(lot.registerVehicle("MH14CD5678", "CAR"), kWednesday1000).getSlotNumber(),
             std::string("1"));
}

TEST_CASE(cancel_frees_slot_and_charges_nothing) {
    ParkingLot lot = smallLot(1);
    lot.parkVehicle(lot.registerVehicle("MH12AB1234", "CAR"), kWednesday1000);
    const auto cancelled = lot.cancelParking("MH12AB1234", kWednesday1000 + std::chrono::seconds(300));
    CHECK(cancelled.getStatus() == TransactionStatus::Cancelled);
    CHECK_NEAR(cancelled.getFee()->totalAmount, 0.0);
    CHECK(!cancelled.getPayment().has_value());
    CHECK(lot.findSlot("1")->isAvailable());
}

// --- 4. Duration ---------------------------------------------------------------

TEST_CASE(parking_duration_is_exit_minus_entry_in_seconds) {
    ParkingLot lot = smallLot(1);
    lot.parkVehicle(lot.registerVehicle("MH12AB1234", "CAR"), kWednesday1000);
    CHECK_THROWS_AS(lot.findActiveTransaction("MH12AB1234")->calculateDuration(), InvalidSessionStateException);
    const auto done = lot.removeVehicle("MH12AB1234", kWednesday1000 + std::chrono::seconds(3725), PaymentMethod::Cash);
    CHECK_EQ(done.calculateDuration(), 3725LL);
    CHECK_EQ(done.getFee()->totalMinutes, 3725LL);  // 1 s billed as 1 minute (parkinglot.c rule)
}

// --- 6. Invalid state transitions ------------------------------------------------

TEST_CASE(invalid_session_transitions_are_rejected) {
    const auto car = std::make_shared<FourWheeler>(1, "MH12AB1234");
    const auto strategy = createFeeStrategy(AppConfig::defaults(), "CAR");
    ParkingTransaction transaction(1, car, "1");

    CHECK_THROWS_AS(transaction.endSession(kWednesday1000, *strategy), InvalidSessionStateException);   // not started
    CHECK_THROWS_AS(transaction.cancelTransaction(kWednesday1000), InvalidSessionStateException);
    CHECK_THROWS_AS(transaction.calculateFee(*strategy, kWednesday1000), InvalidSessionStateException);

    transaction.startSession(kWednesday1000);
    CHECK_THROWS_AS(transaction.startSession(kWednesday1000), InvalidSessionStateException);           // twice
    CHECK_THROWS_AS(transaction.settlePayment(PaymentMethod::Cash, kWednesday1000), InvalidSessionStateException);
    CHECK_THROWS_AS(transaction.endSession(kWednesday1000, *strategy), ValidationException);            // exit == entry
    CHECK(transaction.isActive());  // a rejected exit changes nothing

    transaction.endSession(kWednesday1000 + std::chrono::seconds(60), *strategy);
    CHECK_THROWS_AS(transaction.endSession(kWednesday1000 + std::chrono::seconds(120), *strategy),
                    InvalidSessionStateException);                                                     // closed twice
    CHECK_THROWS_AS(transaction.cancelTransaction(kWednesday1000), InvalidSessionStateException);
    transaction.settlePayment(PaymentMethod::Upi, kWednesday1000 + std::chrono::seconds(60));
    CHECK_THROWS_AS(transaction.settlePayment(PaymentMethod::Cash, kWednesday1000), InvalidSessionStateException);
    CHECK(transaction.getPayment()->getPaymentStatus() == PaymentStatus::Success);
    CHECK(transaction.getPayment()->getPaymentMethod() == PaymentMethod::Upi);
}

TEST_CASE(exit_for_unknown_plate_is_not_found) {
    ParkingLot lot = smallLot(1);
    CHECK_THROWS_AS(lot.removeVehicle("MH12AB1234", kWednesday1000, PaymentMethod::Cash), NotFoundException);
    CHECK_THROWS_AS(lot.cancelParking("MH12AB1234", kWednesday1000), NotFoundException);
}

TEST_CASE(payment_validation) {
    CHECK_THROWS_AS(Payment(1, 1, -5.0), ValidationException);
    CHECK_THROWS_AS(parsePaymentMethod("BITCOIN"), ValidationException);
    CHECK(parsePaymentMethod("UPI") == PaymentMethod::Upi);
    Payment payment(1, 1, 10.0);
    CHECK(payment.getPaymentStatus() == PaymentStatus::Pending);
    payment.processPayment(PaymentMethod::Card, kWednesday1000);
    CHECK(payment.getPaymentStatus() == PaymentStatus::Success);
}

// --- 11. Custom templates --------------------------------------------------------

TEST_CASE(require_in_range_template_works_for_several_types) {
    CHECK_EQ(requireInRange(18, 0, 23, "hour"), 18);
    CHECK_EQ(requireInRange(0, 0, 23, "hour"), 0);    // inclusive bounds
    CHECK_EQ(requireInRange(23, 0, 23, "hour"), 23);
    CHECK_THROWS_AS(requireInRange(24, 0, 23, "hour"), ValidationException);
    CHECK_NEAR(requireInRange(0.67, 0.0, 10.0, "rate"), 0.67);
    CHECK_THROWS_AS(requireInRange(-0.01, 0.0, 10.0, "rate"), ValidationException);
    CHECK_THROWS_AS(requireInRange(5LL, 10LL, 20LL, "count"), ValidationException);
    try {
        requireInRange(30, 0, 23, "peak_start_hour");
    } catch (const ValidationException& e) {
        CHECK(std::string(e.what()).find("peak_start_hour") != std::string::npos);
    }
}

TEST_CASE(find_or_null_template_works_for_map_types) {
    std::map<std::string, int> ordered = {{"A", 1}};
    std::unordered_map<int, std::string> hashed = {{7, "seven"}};
    const std::map<std::string, int>& constOrdered = ordered;

    CHECK(findOrNull(ordered, std::string("missing")) == nullptr);
    *findOrNull(ordered, std::string("A")) = 5;   // non-const map -> writable pointer
    CHECK_EQ(ordered["A"], 5);
    CHECK_EQ(*findOrNull(constOrdered, std::string("A")), 5);  // const map -> const pointer
    CHECK_EQ(*findOrNull(hashed, 7), std::string("seven"));
    CHECK(findOrNull(hashed, 8) == nullptr);
}

// --- Restoring saved state -------------------------------------------------------

TEST_CASE(restore_rejects_two_active_sessions_in_one_slot) {
    ParkingLot lot = smallLot(2);
    TransactionRecord first;
    first.transactionId = 1;
    first.numberPlate = "MH12AB1234";
    first.slotNumber = "1";
    first.status = "ACTIVE";
    first.entryTime = kWednesday1000;
    lot.restoreTransaction(first);

    TransactionRecord clash = first;
    clash.transactionId = 2;
    clash.numberPlate = "MH14CD5678";
    CHECK_THROWS_AS(lot.restoreTransaction(clash), SlotUnavailableException);

    TransactionRecord duplicateId = first;
    duplicateId.numberPlate = "MH14CD5678";
    duplicateId.slotNumber = "2";
    CHECK_THROWS_AS(lot.restoreTransaction(duplicateId), ValidationException);

    // New transactions continue after the highest restored id.
    const auto next = lot.parkVehicle(lot.registerVehicle("MH04IJ7890", "CAR"), kWednesday1000);
    CHECK_EQ(next.getTransactionId(), 2);
    CHECK_EQ(next.getSlotNumber(), std::string("2"));
}
