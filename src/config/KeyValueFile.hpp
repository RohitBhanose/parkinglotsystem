#pragma once

#include <string>
#include <utility>
#include <vector>

namespace parking {

struct KeyValueEntry {
    std::string key;
    std::string value;
    int lineNumber = 0;
};

// Reads simple "key = value" files (config/parking.cfg, .env).
// Blank lines and lines starting with '#' are skipped; surrounding quotes on
// the value are removed. Repeated keys are kept in order (used for `slots`).
// Throws StorageException if the file cannot be opened, and
// ValidationException for a line without '='.
std::vector<KeyValueEntry> readKeyValueFile(const std::string& path);

std::string trim(const std::string& text);

}  // namespace parking
