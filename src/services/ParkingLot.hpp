#pragma once

#include <iosfwd>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "config/AppConfig.hpp"
#include "models/ParkingSlot.hpp"
#include "models/ParkingTransaction.hpp"
#include "models/Vehicle.hpp"
#include "services/ParkingFeeStrategy.hpp"
#include "storage/TransactionRecord.hpp"

namespace parking {

// Coordinates the facility: slots, vehicles, sessions and pricing.
// Business rules enforced here (all carried over from the original system):
//   * the first free slot in slot order is assigned,
//   * a vehicle can have only one active session,
//   * a slot can have only one active session,
//   * the fee is computed by the vehicle type's ParkingFeeStrategy at exit.
// It never touches files - persistence is ParkingRecordManager's job.
class ParkingLot {
public:
    ParkingLot(std::string name, std::vector<ParkingSlot> slots, const AppConfig& config);

    // Owns unique_ptr strategies and indexes into its own vectors: not copyable.
    ParkingLot(const ParkingLot&) = delete;
    ParkingLot& operator=(const ParkingLot&) = delete;
    ParkingLot(ParkingLot&&) = default;
    ParkingLot& operator=(ParkingLot&&) = default;

    const std::string& getName() const { return name_; }

    // Returns the vehicle already known for this plate, or creates a new one
    // (TwoWheeler / FourWheeler) with the next vehicle id.
    std::shared_ptr<const Vehicle> registerVehicle(const std::string& numberPlate, const std::string& vehicleType);

    ParkingSlot* findAvailableSlot();
    const ParkingSlot* findSlot(const std::string& slotNumber) const;

    // Entry. Throws InvalidSessionStateException ("ALREADY_PARKED") or SlotUnavailableException.
    ParkingTransaction parkVehicle(const std::shared_ptr<const Vehicle>& vehicle, TimePoint entryTime);
    // Exit: ends the session, prices it, records the payment, frees the slot.
    ParkingTransaction removeVehicle(const std::string& numberPlate, TimePoint exitTime, PaymentMethod method);
    // Cancels an active session without charge and frees the slot.
    ParkingTransaction cancelParking(const std::string& numberPlate, TimePoint cancelTime);

    std::optional<ParkingTransaction> findActiveTransaction(const std::string& numberPlate) const;
    std::optional<ParkingTransaction> findTransactionById(int transactionId) const;
    FeeBreakdown estimateFee(const std::string& numberPlate, TimePoint until) const;

    const std::vector<ParkingSlot>& getSlots() const { return slots_; }
    std::vector<const ParkingSlot*> getAvailableSlots() const;
    std::vector<const ParkingSlot*> getOccupiedSlots() const;
    // Newest entry first; an empty plate means "all vehicles".
    std::vector<ParkingTransaction> getParkingHistory(const std::string& numberPlate = "") const;
    void displayParkingStatus(std::ostream& out) const;

    const ParkingFeeStrategy& strategyFor(const std::string& vehicleType) const;

    // Re-applies a saved transaction (used when loading records).
    // Throws if it conflicts with what is already loaded.
    void restoreTransaction(const TransactionRecord& record);

private:
    ParkingTransaction& activeTransactionFor(const std::string& numberPlate);
    ParkingSlot& slotByNumber(const std::string& slotNumber);

    std::string name_;
    std::vector<ParkingSlot> slots_;
    std::unordered_map<std::string, std::size_t> slotIndexByNumber_;
    std::vector<ParkingTransaction> transactions_;                     // full history, in entry order
    std::unordered_map<int, std::size_t> transactionIndexById_;
    std::unordered_map<std::string, std::size_t> activeIndexByPlate_;  // plate -> index in transactions_
    std::unordered_map<std::string, std::shared_ptr<const Vehicle>> vehicles_;
    std::unordered_map<std::string, std::unique_ptr<ParkingFeeStrategy>> strategies_;  // by vehicle type
    int nextTransactionId_ = 1;
    int nextVehicleId_ = 1;
};

}  // namespace parking
