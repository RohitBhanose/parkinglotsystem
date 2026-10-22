#pragma once

#include <iosfwd>
#include <optional>
#include <string>

namespace parking {

// One parking bay. The only way to change its occupancy is through
// assignVehicle()/releaseVehicle(), which enforce "one active session per slot".
class ParkingSlot {
public:
    ParkingSlot(int slotId, std::string slotNumber, char zone, int floor, std::string slotType);

    int getSlotId() const { return slotId_; }
    const std::string& getSlotNumber() const { return slotNumber_; }
    char getZone() const { return zone_; }
    int getFloor() const { return floor_; }
    const std::string& getSlotType() const { return slotType_; }

    bool isAvailable() const { return !activeTransactionId_.has_value(); }
    std::optional<int> getActiveTransactionId() const { return activeTransactionId_; }
    const std::string& getOccupantPlate() const { return occupantPlate_; }
    std::string getStatus() const { return isAvailable() ? "AVAILABLE" : "OCCUPIED"; }

    // Throws SlotUnavailableException if the slot is already occupied.
    void assignVehicle(int transactionId, const std::string& numberPlate);
    // Throws InvalidSessionStateException if the slot is free or held by another session.
    void releaseVehicle(int transactionId);

    void displayStatus(std::ostream& out) const;

private:
    int slotId_;
    std::string slotNumber_;
    char zone_;
    int floor_;
    std::string slotType_;
    std::optional<int> activeTransactionId_;
    std::string occupantPlate_;
};

}  // namespace parking
