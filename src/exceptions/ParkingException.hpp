#pragma once

#include <stdexcept>
#include <string>
#include <utility>

namespace parking {

// Base class for every error the parking core raises on purpose.
// `code()` is a short machine-readable tag (e.g. "NO_SLOT_AVAILABLE") that the
// command-line front end forwards to Python so the UI can react to it.
class ParkingException : public std::runtime_error {
public:
    ParkingException(std::string code, const std::string& message)
        : std::runtime_error(message), code_(std::move(code)) {}

    const std::string& code() const noexcept { return code_; }

private:
    std::string code_;
};

// Bad data: an invalid plate, a negative amount, a malformed config value.
class ValidationException : public ParkingException {
public:
    explicit ValidationException(const std::string& message)
        : ParkingException("VALIDATION_ERROR", message) {}
};

// Every slot in the lot is occupied (or the requested slot is taken).
class SlotUnavailableException : public ParkingException {
public:
    explicit SlotUnavailableException(const std::string& message)
        : ParkingException("NO_SLOT_AVAILABLE", message) {}
};

// An operation that is not allowed in the current session state, such as
// ending a session twice or parking a vehicle that is already parked.
class InvalidSessionStateException : public ParkingException {
public:
    explicit InvalidSessionStateException(const std::string& message,
                                          std::string code = "INVALID_SESSION_STATE")
        : ParkingException(std::move(code), message) {}
};

// A vehicle, transaction or slot that was asked for does not exist.
class NotFoundException : public ParkingException {
public:
    explicit NotFoundException(const std::string& message)
        : ParkingException("NOT_FOUND", message) {}
};

// File read/write failures and corrupt record files.
class StorageException : public ParkingException {
public:
    explicit StorageException(const std::string& message)
        : ParkingException("STORAGE_ERROR", message) {}
};

// MySQL connection or query failures (optional MySQL backend only).
class DatabaseException : public ParkingException {
public:
    explicit DatabaseException(const std::string& message)
        : ParkingException("DATABASE_ERROR", message) {}
};

}  // namespace parking
