#include "config/KeyValueFile.hpp"

#include <fstream>

#include "exceptions/ParkingException.hpp"

namespace parking {

std::string trim(const std::string& text) {
    const char* whitespace = " \t\r\n";
    const auto first = text.find_first_not_of(whitespace);
    if (first == std::string::npos) {
        return "";
    }
    const auto last = text.find_last_not_of(whitespace);
    return text.substr(first, last - first + 1);
}

std::vector<KeyValueEntry> readKeyValueFile(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw StorageException("Cannot open '" + path + "' for reading");
    }

    std::vector<KeyValueEntry> entries;
    std::string line;
    int lineNumber = 0;
    while (std::getline(in, line)) {
        ++lineNumber;
        if (lineNumber == 1 && line.rfind("\xEF\xBB\xBF", 0) == 0) {
            line.erase(0, 3);  // UTF-8 byte-order mark written by some Windows editors
        }
        line = trim(line);
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const auto equals = line.find('=');
        if (equals == std::string::npos) {
            throw ValidationException(path + ":" + std::to_string(lineNumber) + ": expected 'key = value'");
        }
        std::string value = trim(line.substr(equals + 1));
        if (value.size() >= 2 && (value.front() == '"' || value.front() == '\'') && value.back() == value.front()) {
            value = value.substr(1, value.size() - 2);
        }
        entries.push_back({trim(line.substr(0, equals)), value, lineNumber});
    }
    if (in.bad()) {
        throw StorageException("Error while reading '" + path + "'");
    }
    return entries;
}

}  // namespace parking
