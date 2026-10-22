#pragma once

#include <iosfwd>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "config/AppConfig.hpp"
#include "storage/ParkingRepository.hpp"

namespace parking {

class JsonObject;
class ParkingLot;
class ParkingTransaction;

// The parkinglot executable's command-line interface.
//
//   parkinglot <entry_ts> <exit_ts> [cancel]   legacy fare mode - same
//                                               KEY=VALUE output as parkinglot.c
//   parkinglot <command> [args] [--options]    JSON mode used by Python
//   parkinglot demo                             OOP demonstration
//
// Every JSON reply has "ok": true/false; failures also carry "error_code" and
// "message" and exit with status 1, so Python can show a clear error.
class CommandLineApp {
public:
    CommandLineApp(std::ostream& out, std::ostream& err);
    int run(const std::vector<std::string>& args);

private:
    struct Options {
        std::vector<std::string> positional;
        std::map<std::string, std::string> named;
        std::string get(const std::string& name, const std::string& fallback = "") const;
        bool has(const std::string& name) const { return named.count(name) > 0; }
    };

    static bool parseOptions(const std::vector<std::string>& args, Options& options, std::string& error);
    int runLegacyFare(const std::vector<std::string>& args);
    int runCommand(const Options& options);
    int dispatch(const Options& options);
    int usageError(const std::string& message);
    void printHelp() const;

    AppConfig loadConfig(const Options& options) const;
    std::unique_ptr<ParkingRepository> makeRepository(const AppConfig& config, const Options& options) const;

    JsonObject transactionJson(const ParkingTransaction& transaction, const ParkingLot& lot) const;

    std::ostream& out_;
    std::ostream& err_;
};

}  // namespace parking
