#include "services/ParkingLot.hpp"

#include <algorithm>
#include <ostream>

#include "exceptions/ParkingException.hpp"
#include "util/Validation.hpp"

namespace parking {

ParkingLot::ParkingLot(std::string name, std::vector<ParkingSlot> slots, const AppConfig& config)
    : name_(std::move(name)), slots_(std::move(slots)) {
    if (slots_.empty()) {
        throw ValidationException("A parking lot needs at least one slot");
    }
    for (std::size_t i = 0; i < slots_.size(); ++i) {
        if (!slotIndexByNumber_.emplace(slots_[i].getSlotNumber(), i).second) {
            throw ValidationException("Duplicate slot number " + slots_[i].getSlotNumber());
        }
    }
    for (const auto& [vehicleType, rates] : config.getRateCards()) {
        (void)rates;
        strategies_[vehicleType] = createFeeStrategy(config, vehicleType);
    }
}

std::shared_ptr<const Vehicle> ParkingLot::registerVehicle(const std::string& numberPlate,
                                                           const std::string& vehicleType) {
    const std::string plate = Vehicle::normalizePlate(numberPlate);
    if (const auto* known = findOrNull(vehicles_, plate)) {
        if ((*known)->getVehicleType() == vehicleType) {
            return *known;
        }
        // Same plate registered with a different type: keep its id, update the type.
        auto updated = createVehicle((*known)->getVehicleId(), plate, vehicleType);
        vehicles_[plate] = updated;
        return updated;
    }
    auto vehicle = createVehicle(nextVehicleId_, plate, vehicleType);
    ++nextVehicleId_;
    vehicles_[plate] = vehicle;
    return vehicle;
}

ParkingSlot* ParkingLot::findAvailableSlot() {
    auto it = std::find_if(slots_.begin(), slots_.end(), [](const ParkingSlot& slot) { return slot.isAvailable(); });
    return it == slots_.end() ? nullptr : &*it;
}

const ParkingSlot* ParkingLot::findSlot(const std::string& slotNumber) const {
    const std::size_t* index = findOrNull(slotIndexByNumber_, slotNumber);
    return index == nullptr ? nullptr : &slots_[*index];
}

ParkingSlot& ParkingLot::slotByNumber(const std::string& slotNumber) {
    const std::size_t* index = findOrNull(slotIndexByNumber_, slotNumber);
    if (index == nullptr) {
        throw NotFoundException("Slot " + slotNumber + " does not exist in " + name_);
    }
    return slots_[*index];
}

ParkingTransaction ParkingLot::parkVehicle(const std::shared_ptr<const Vehicle>& vehicle, TimePoint entryTime) {
    if (!vehicle) {
        throw ValidationException("Cannot park a null vehicle");
    }
    const std::string& plate = vehicle->getNumberPlate();
    if (findOrNull(activeIndexByPlate_, plate) != nullptr) {
        throw InvalidSessionStateException(plate + " is already parked", "ALREADY_PARKED");
    }
    strategyFor(vehicle->getVehicleType());  // fail at entry, not at exit, if the type has no tariff

    ParkingSlot* slot = findAvailableSlot();
    if (slot == nullptr) {
        throw SlotUnavailableException("No available parking slots in " + name_);
    }

    if (findOrNull(vehicles_, plate) == nullptr) {
        vehicles_[plate] = vehicle;
        nextVehicleId_ = std::max(nextVehicleId_, vehicle->getVehicleId() + 1);
    }

    ParkingTransaction transaction(nextTransactionId_, vehicle, slot->getSlotNumber());
    transaction.startSession(entryTime);
    slot->assignVehicle(transaction.getTransactionId(), plate);

    ++nextTransactionId_;
    transactions_.push_back(transaction);
    transactionIndexById_[transaction.getTransactionId()] = transactions_.size() - 1;
    activeIndexByPlate_[plate] = transactions_.size() - 1;
    return transaction;
}

ParkingTransaction& ParkingLot::activeTransactionFor(const std::string& numberPlate) {
    const std::size_t* index = findOrNull(activeIndexByPlate_, Vehicle::normalizePlate(numberPlate));
    if (index == nullptr) {
        throw NotFoundException("No active parking session for " + Vehicle::normalizePlate(numberPlate));
    }
    return transactions_[*index];
}

ParkingTransaction ParkingLot::removeVehicle(const std::string& numberPlate, TimePoint exitTime,
                                             PaymentMethod method) {
    ParkingTransaction& transaction = activeTransactionFor(numberPlate);
    // The vehicle's own category decides which tariff object prices the stay.
    transaction.endSession(exitTime, strategyFor(transaction.getVehicle().getVehicleType()));
    slotByNumber(transaction.getSlotNumber()).releaseVehicle(transaction.getTransactionId());
    activeIndexByPlate_.erase(transaction.getVehicle().getNumberPlate());
    transaction.settlePayment(method, exitTime);
    return transaction;
}

ParkingTransaction ParkingLot::cancelParking(const std::string& numberPlate, TimePoint cancelTime) {
    ParkingTransaction& transaction = activeTransactionFor(numberPlate);
    transaction.cancelTransaction(cancelTime);
    slotByNumber(transaction.getSlotNumber()).releaseVehicle(transaction.getTransactionId());
    activeIndexByPlate_.erase(transaction.getVehicle().getNumberPlate());
    return transaction;
}

std::optional<ParkingTransaction> ParkingLot::findActiveTransaction(const std::string& numberPlate) const {
    const std::size_t* index = findOrNull(activeIndexByPlate_, Vehicle::normalizePlate(numberPlate));
    if (index == nullptr) {
        return std::nullopt;
    }
    return transactions_[*index];
}

std::optional<ParkingTransaction> ParkingLot::findTransactionById(int transactionId) const {
    const std::size_t* index = findOrNull(transactionIndexById_, transactionId);
    if (index == nullptr) {
        return std::nullopt;
    }
    return transactions_[*index];
}

FeeBreakdown ParkingLot::estimateFee(const std::string& numberPlate, TimePoint until) const {
    const auto active = findActiveTransaction(numberPlate);
    if (!active) {
        throw NotFoundException("No active parking session for " + Vehicle::normalizePlate(numberPlate));
    }
    return active->calculateFee(strategyFor(active->getVehicle().getVehicleType()), until);
}

std::vector<const ParkingSlot*> ParkingLot::getAvailableSlots() const {
    std::vector<const ParkingSlot*> result;
    for (const auto& slot : slots_) {
        if (slot.isAvailable()) {
            result.push_back(&slot);
        }
    }
    return result;
}

std::vector<const ParkingSlot*> ParkingLot::getOccupiedSlots() const {
    std::vector<const ParkingSlot*> result;
    for (const auto& slot : slots_) {
        if (!slot.isAvailable()) {
            result.push_back(&slot);
        }
    }
    return result;
}

std::vector<ParkingTransaction> ParkingLot::getParkingHistory(const std::string& numberPlate) const {
    const std::string plate = Vehicle::normalizePlate(numberPlate);
    std::vector<ParkingTransaction> history;
    std::copy_if(transactions_.begin(), transactions_.end(), std::back_inserter(history),
                 [&plate](const ParkingTransaction& t) { return plate.empty() || t.getVehicle().getNumberPlate() == plate; });
    std::stable_sort(history.begin(), history.end(), [](const ParkingTransaction& a, const ParkingTransaction& b) {
        return a.getEntryTime() > b.getEntryTime();
    });
    return history;
}

void ParkingLot::displayParkingStatus(std::ostream& out) const {
    out << name_ << ": " << getOccupiedSlots().size() << " occupied / " << slots_.size() << " slots\n";
    for (const auto& slot : slots_) {
        out << "  ";
        slot.displayStatus(out);
        out << '\n';
    }
}

const ParkingFeeStrategy& ParkingLot::strategyFor(const std::string& vehicleType) const {
    const auto* strategy = findOrNull(strategies_, vehicleType);
    if (strategy == nullptr) {
        throw ValidationException("No tariff configured for vehicle type '" + vehicleType + "'");
    }
    return **strategy;
}

void ParkingLot::restoreTransaction(const TransactionRecord& record) {
    if (findOrNull(transactionIndexById_, record.transactionId) != nullptr) {
        throw ValidationException("Duplicate transaction id #" + std::to_string(record.transactionId));
    }
    auto vehicle = registerVehicle(record.numberPlate, record.vehicleType);
    ParkingTransaction transaction = ParkingTransaction::fromRecord(record, vehicle);

    if (transaction.isActive()) {
        const std::string& plate = vehicle->getNumberPlate();
        if (findOrNull(activeIndexByPlate_, plate) != nullptr) {
            throw InvalidSessionStateException(plate + " has two ACTIVE sessions in the records");
        }
        slotByNumber(transaction.getSlotNumber()).assignVehicle(transaction.getTransactionId(), plate);
        activeIndexByPlate_[plate] = transactions_.size();
    }
    transactions_.push_back(transaction);
    transactionIndexById_[transaction.getTransactionId()] = transactions_.size() - 1;
    nextTransactionId_ = std::max(nextTransactionId_, transaction.getTransactionId() + 1);
}

}  // namespace parking
