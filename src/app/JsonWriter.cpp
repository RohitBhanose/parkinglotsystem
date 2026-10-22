#include "app/JsonWriter.hpp"

#include <cstdio>
#include <iomanip>
#include <sstream>

namespace parking {

std::string jsonEscape(const std::string& text) {
    std::string out = "\"";
    for (unsigned char c : text) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buffer[8];
                    std::snprintf(buffer, sizeof(buffer), "\\u%04x", c);
                    out += buffer;
                } else {
                    out += static_cast<char>(c);
                }
        }
    }
    return out + "\"";
}

JsonObject& JsonObject::addRaw(const std::string& key, std::string rawValue) {
    fields_.emplace_back(key, std::move(rawValue));
    return *this;
}

JsonObject& JsonObject::add(const std::string& key, const std::string& value) { return addRaw(key, jsonEscape(value)); }
JsonObject& JsonObject::add(const std::string& key, const char* value) { return addRaw(key, jsonEscape(value)); }
JsonObject& JsonObject::add(const std::string& key, int value) { return addRaw(key, std::to_string(value)); }
JsonObject& JsonObject::add(const std::string& key, long long value) { return addRaw(key, std::to_string(value)); }
JsonObject& JsonObject::add(const std::string& key, bool value) { return addRaw(key, value ? "true" : "false"); }
JsonObject& JsonObject::add(const std::string& key, const JsonObject& value) { return addRaw(key, value.str()); }
JsonObject& JsonObject::add(const std::string& key, const JsonArray& value) { return addRaw(key, value.str()); }
JsonObject& JsonObject::addNull(const std::string& key) { return addRaw(key, "null"); }

JsonObject& JsonObject::add(const std::string& key, double value, int decimals) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(decimals) << value;
    return addRaw(key, out.str());
}

std::string JsonObject::str() const {
    std::string out = "{";
    for (std::size_t i = 0; i < fields_.size(); ++i) {
        out += (i == 0 ? "" : ",") + jsonEscape(fields_[i].first) + ":" + fields_[i].second;
    }
    return out + "}";
}

JsonArray& JsonArray::push(const JsonObject& value) {
    items_.push_back(value.str());
    return *this;
}

JsonArray& JsonArray::push(const std::string& value) {
    items_.push_back(jsonEscape(value));
    return *this;
}

std::string JsonArray::str() const {
    std::string out = "[";
    for (std::size_t i = 0; i < items_.size(); ++i) {
        out += (i == 0 ? "" : ",") + items_[i];
    }
    return out + "]";
}

}  // namespace parking
