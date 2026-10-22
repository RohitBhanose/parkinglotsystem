#pragma once

#include <string>
#include <utility>
#include <vector>

namespace parking {

class JsonArray;

// Minimal JSON builder for the CLI's structured output to Python.
// Keys keep insertion order; values are serialised as they are added.
class JsonObject {
public:
    JsonObject& add(const std::string& key, const std::string& value);
    JsonObject& add(const std::string& key, const char* value);
    JsonObject& add(const std::string& key, int value);
    JsonObject& add(const std::string& key, long long value);
    JsonObject& add(const std::string& key, bool value);
    // Doubles are written with a fixed number of decimals (money = 2).
    JsonObject& add(const std::string& key, double value, int decimals = 2);
    JsonObject& add(const std::string& key, const JsonObject& value);
    JsonObject& add(const std::string& key, const JsonArray& value);
    JsonObject& addNull(const std::string& key);

    std::string str() const;

private:
    JsonObject& addRaw(const std::string& key, std::string rawValue);
    std::vector<std::pair<std::string, std::string>> fields_;
};

class JsonArray {
public:
    JsonArray& push(const JsonObject& value);
    JsonArray& push(const std::string& value);
    std::string str() const;

private:
    std::vector<std::string> items_;
};

std::string jsonEscape(const std::string& text);

}  // namespace parking
