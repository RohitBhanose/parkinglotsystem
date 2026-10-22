#include "models/ParkingSlot.hpp"

#include <ostream>

#include "exceptions/ParkingException.hpp"

namespace parking {

ParkingSlot::ParkingSlot(int slotId, std::string slotNumber, char zone, int floor, std::string slotType)
    : slotId_(slotId), slotNumber_(std::move(slotNumber)), zone_(zone), floor_(floor), slotType_(std::move(slotType)) {
    if (slotId_ <= 0 || slotNumber_.empty()) {
        throw ValidationException("A parking slot needs a positive id and a slot number");
    }
}

void ParkingSlot::assignVehicle(int transactionId, const std::string& numberPlate) {
    if (!isAvailable()) {
        throw SlotUnavailableException("Slot " + slotNumber_ + " is already occupied by " + occupantPlate_);
    }
    activeTransactionId_ = transactionId;
    occupantPlate_ = numberPlate;
}

void ParkingSlot::releaseVehicle(int transactionId) {
    if (isAvailable()) {
        throw InvalidSessionStateException("Slot " + slotNumber_ + " is already free");
    }
    if (*activeTransactionId_ != transactionId) {
        throw InvalidSessionStateException("Slot " + slotNumber_ + " is held by transaction #" +
                                           std::to_string(*activeTransactionId_) + ", not #" +
                                           std::to_string(transactionId));
    }
    activeTransactionId_.reset();
    occupantPlate_.clear();
}

void ParkingSlot::displayStatus(std::ostream& out) const {
    out << "Slot " << slotNumber_ << " (zone " << zone_ << ", floor " << floor_ << ", " << slotType_ << "): ";
    if (isAvailable()) {
        out << "AVAILABLE";
    } else {
        out << "OCCUPIED by " << occupantPlate_ << " (transaction #" << *activeTransactionId_ << ")";
    }
}

}  // namespace parking
