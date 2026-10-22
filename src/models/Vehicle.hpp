#pragma once

#include <iosfwd>
#include <memory>
#include <string>

namespace parking {

// Abstract base class for every vehicle the lot can park.
// Common data (id, plate, type code) lives here once; the derived classes
// only add what is specific to their category.
class Vehicle {
public:
    virtual ~Vehicle() = default;

    int getVehicleId() const { return vehicleId_; }
    const std::string& getNumberPlate() const { return numberPlate_; }

    // Type code shared with the MySQL schema: "CAR" or "BIKE".
    // It also selects the vehicle's rate card in config/parking.cfg.
    const std::string& getVehicleType() const { return vehicleType_; }

    virtual int getWheelCount() const = 0;
    virtual std::string getCategoryName() const = 0;
    virtual void displayDetails(std::ostream& out) const;

    // "mh 12-ab 1234" -> "MH12AB1234" (spaces, dashes and dots are dropped).
    static std::string normalizePlate(const std::string& raw);
    // 4-15 characters, A-Z and 0-9 only, at least one letter and one digit.
    static bool isValidPlate(const std::string& plate);

protected:
    // Only derived classes may construct a Vehicle.
    Vehicle(int vehicleId, const std::string& numberPlate, std::string vehicleType);

private:
    int vehicleId_;
    std::string numberPlate_;
    std::string vehicleType_;
};

class TwoWheeler : public Vehicle {
public:
    static constexpr const char* TYPE_CODE = "BIKE";

    TwoWheeler(int vehicleId, const std::string& numberPlate);

    int getWheelCount() const override { return 2; }
    std::string getCategoryName() const override { return "Two-wheeler"; }
    void displayDetails(std::ostream& out) const override;
};

class FourWheeler : public Vehicle {
public:
    static constexpr const char* TYPE_CODE = "CAR";

    FourWheeler(int vehicleId, const std::string& numberPlate);

    int getWheelCount() const override { return 4; }
    std::string getCategoryName() const override { return "Four-wheeler"; }
    void displayDetails(std::ostream& out) const override;
};

// Creates the right derived class for a type code ("CAR" / "BIKE").
// Throws ValidationException for an unknown type or an invalid plate.
std::shared_ptr<Vehicle> createVehicle(int vehicleId, const std::string& numberPlate,
                                       const std::string& vehicleType);

bool isSupportedVehicleType(const std::string& vehicleType);

}  // namespace parking
