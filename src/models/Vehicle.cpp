#include "models/Vehicle.hpp"

#include <algorithm>
#include <cctype>
#include <ostream>

#include "exceptions/ParkingException.hpp"

namespace parking {

Vehicle::Vehicle(int vehicleId, const std::string& numberPlate, std::string vehicleType)
    : vehicleId_(vehicleId), numberPlate_(normalizePlate(numberPlate)), vehicleType_(std::move(vehicleType)) {
    if (vehicleId_ <= 0) {
        throw ValidationException("Vehicle id must be positive");
    }
    if (!isValidPlate(numberPlate_)) {
        throw ValidationException("Invalid number plate '" + numberPlate + "'");
    }
}

void Vehicle::displayDetails(std::ostream& out) const {
    out << "Vehicle #" << vehicleId_ << "  plate=" << numberPlate_ << "  type=" << vehicleType_
        << "  (" << getCategoryName() << ", " << getWheelCount() << " wheels)";
}

std::string Vehicle::normalizePlate(const std::string& raw) {
    std::string plate;
    for (unsigned char c : raw) {
        if (c == ' ' || c == '-' || c == '.' || c == '\t') {
            continue;
        }
        plate += static_cast<char>(std::toupper(c));
    }
    return plate;
}

bool Vehicle::isValidPlate(const std::string& plate) {
    if (plate.size() < 4 || plate.size() > 15) {
        return false;
    }
    const auto isUpperAlnum = [](unsigned char c) { return std::isdigit(c) || (c >= 'A' && c <= 'Z'); };
    const auto isDigit = [](unsigned char c) { return std::isdigit(c) != 0; };
    const auto isLetter = [](unsigned char c) { return c >= 'A' && c <= 'Z'; };
    return std::all_of(plate.begin(), plate.end(), isUpperAlnum) &&
           std::any_of(plate.begin(), plate.end(), isDigit) &&
           std::any_of(plate.begin(), plate.end(), isLetter);
}

TwoWheeler::TwoWheeler(int vehicleId, const std::string& numberPlate)
    : Vehicle(vehicleId, numberPlate, TYPE_CODE) {}

void TwoWheeler::displayDetails(std::ostream& out) const {
    Vehicle::displayDetails(out);
    out << "  [compact two-wheeler]";
}

FourWheeler::FourWheeler(int vehicleId, const std::string& numberPlate)
    : Vehicle(vehicleId, numberPlate, TYPE_CODE) {}

void FourWheeler::displayDetails(std::ostream& out) const {
    Vehicle::displayDetails(out);
    out << "  [standard four-wheeler]";
}

bool isSupportedVehicleType(const std::string& vehicleType) {
    return vehicleType == TwoWheeler::TYPE_CODE || vehicleType == FourWheeler::TYPE_CODE;
}

std::shared_ptr<Vehicle> createVehicle(int vehicleId, const std::string& numberPlate,
                                       const std::string& vehicleType) {
    if (vehicleType == TwoWheeler::TYPE_CODE) {
        return std::make_shared<TwoWheeler>(vehicleId, numberPlate);
    }
    if (vehicleType == FourWheeler::TYPE_CODE) {
        return std::make_shared<FourWheeler>(vehicleId, numberPlate);
    }
    throw ValidationException("Unsupported vehicle type '" + vehicleType + "' (expected CAR or BIKE)");
}

}  // namespace parking
