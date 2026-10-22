// Fee rules (must match the original parkinglot.c) and runtime polymorphism.

#include <fstream>
#include <random>
#include <sstream>

#include "TestFramework.hpp"
#include "app/CommandLineApp.hpp"
#include "config/AppConfig.hpp"
#include "exceptions/ParkingException.hpp"
#include "services/ParkingFeeStrategy.hpp"
#include "services/ParkingLot.hpp"

using namespace parking;

namespace {

using std::chrono::seconds;

FeeBreakdown carFee(TimePoint entry, TimePoint exit) {
    return createFeeStrategy(AppConfig::defaults(), "CAR")->calculateFee(entry, exit);
}

// Reference oracle: a literal port of the loop in the original parkinglot.c,
// checking every single second. Only used to verify the optimised strategy.
std::pair<long long, long long> referenceMinutes(TimePoint entry, TimePoint exit) {
    long long base = 0, peak = 0;
    for (TimePoint t = entry; t < exit; t += seconds(1)) {
        const std::tm local = timeutil::toLocalTm(t);
        const bool isPeak = local.tm_wday == 0 || local.tm_wday == 6 || (local.tm_hour >= 18 && local.tm_hour < 22);
        (isPeak ? peak : base)++;
    }
    return {base, peak};
}

std::string runCli(const std::vector<std::string>& args, int* exitCode = nullptr) {
    std::ostringstream out, err;
    CommandLineApp app(out, err);
    const int code = app.run(args);
    if (exitCode) *exitCode = code;
    return out.str();
}

}  // namespace

// --- 5. Original fee and surcharge rules -------------------------------------

TEST_CASE(weekday_off_peak_uses_base_rate_only) {
    const TimePoint entry = timeutil::makeLocal(2026, 10, 21, 10, 0, 0);  // Wednesday
    const FeeBreakdown fee = carFee(entry, entry + seconds(150));
    CHECK_EQ(fee.baseMinutes, 150LL);
    CHECK_EQ(fee.peakMinutes, 0LL);
    CHECK_NEAR(fee.baseRate, 0.67);
    CHECK_NEAR(fee.totalAmount, 150 * 0.67);
    CHECK(!fee.isRushHour());
}

TEST_CASE(evening_window_18_to_22_uses_peak_rate) {
    const FeeBreakdown intoPeak = carFee(timeutil::makeLocal(2026, 10, 21, 17, 59, 0),
                                         timeutil::makeLocal(2026, 10, 21, 18, 1, 0));
    CHECK_EQ(intoPeak.baseMinutes, 60LL);
    CHECK_EQ(intoPeak.peakMinutes, 60LL);
    CHECK_NEAR(intoPeak.baseAmount, 60 * 0.67);
    CHECK_NEAR(intoPeak.peakAmount, 60 * 0.80);
    CHECK_NEAR(intoPeak.totalAmount, 60 * 0.67 + 60 * 0.80);
    CHECK(intoPeak.isRushHour());

    const FeeBreakdown outOfPeak = carFee(timeutil::makeLocal(2026, 10, 21, 21, 59, 30),
                                          timeutil::makeLocal(2026, 10, 21, 22, 0, 30));
    CHECK_EQ(outOfPeak.peakMinutes, 30LL);  // 22:00 itself is no longer peak
    CHECK_EQ(outOfPeak.baseMinutes, 30LL);
}

TEST_CASE(weekends_are_peak_all_day) {
    const TimePoint saturday = timeutil::makeLocal(2026, 10, 24, 9, 0, 0);
    const TimePoint sunday = timeutil::makeLocal(2026, 10, 25, 3, 0, 0);
    CHECK_EQ(carFee(saturday, saturday + seconds(100)).peakMinutes, 100LL);
    CHECK_EQ(carFee(sunday, sunday + seconds(100)).peakMinutes, 100LL);
    // Friday 23:59:00 -> Saturday 00:01:00: 60 base + 60 weekend-peak.
    const FeeBreakdown midnight = carFee(timeutil::makeLocal(2026, 10, 23, 23, 59, 0),
                                         timeutil::makeLocal(2026, 10, 24, 0, 1, 0));
    CHECK_EQ(midnight.baseMinutes, 60LL);
    CHECK_EQ(midnight.peakMinutes, 60LL);
}

TEST_CASE(exit_must_be_after_entry) {
    const TimePoint t = timeutil::makeLocal(2026, 10, 21, 10, 0, 0);
    CHECK_THROWS_AS(carFee(t, t), ValidationException);
    CHECK_THROWS_AS(carFee(t, t - seconds(5)), ValidationException);
}

TEST_CASE(optimised_peak_strategy_matches_per_second_reference_loop) {
    std::mt19937 random(2026);
    const TimePoint start = timeutil::makeLocal(2026, 1, 1, 0, 0, 0);
    std::uniform_int_distribution<long long> offset(0, 300LL * 86400);
    std::uniform_int_distribution<long long> length(1, 3LL * 86400);
    for (int i = 0; i < 40; ++i) {
        const TimePoint entry = start + seconds(offset(random));
        const TimePoint exit = entry + seconds(length(random));
        const auto [base, peak] = referenceMinutes(entry, exit);
        const FeeBreakdown fee = carFee(entry, exit);
        CHECK_EQ(fee.baseMinutes, base);
        CHECK_EQ(fee.peakMinutes, peak);
        CHECK_EQ(fee.totalMinutes, base + peak);
    }
}

TEST_CASE(legacy_cli_output_matches_parkinglot_c_format) {
    const long long entry = timeutil::toUnix(timeutil::makeLocal(2026, 10, 21, 17, 59, 0));
    int code = -1;
    const std::string output = runCli({std::to_string(entry), std::to_string(entry + 120)}, &code);
    CHECK_EQ(code, 0);
    CHECK_EQ(output, std::string("STATUS=ACTIVE\nTOTAL_DURATION=120\nBASE_MINUTES=60\nBASE_RATE=0.67\n"
                                 "BASE_AMOUNT=40.20\nPEAK_MINUTES=60\nPEAK_SURCHARGE=0.80\nPEAK_AMOUNT=48.00\n"
                                 "TOTAL_AMOUNT=88.20\n"));

    CHECK_EQ(runCli({"100", "200", "cancel"}, &code), std::string("STATUS=CANCELLED\nAMOUNT=0\n"));
    CHECK_EQ(code, 0);
    CHECK_EQ(runCli({"200", "100"}, &code), std::string("ERROR=Invalid time\n"));
    CHECK_EQ(code, 1);
    CHECK_EQ(runCli({"100", "100", "cancel"}, &code), std::string("ERROR=Invalid time\n"));  // checked before cancel
    CHECK_EQ(runCli({"100"}, &code), std::string("ERROR=Invalid input\n"));
    CHECK_EQ(code, 1);
}

// --- 10. Runtime polymorphism ------------------------------------------------------

TEST_CASE(fee_strategy_is_chosen_at_runtime_through_base_class) {
    const AppConfig config = AppConfig::defaults();
    const TimePoint entry = timeutil::makeLocal(2026, 10, 21, 17, 59, 0);
    const TimePoint exit = entry + seconds(120);

    std::vector<std::unique_ptr<ParkingFeeStrategy>> strategies;
    strategies.push_back(std::make_unique<PeakHourFeeStrategy>(config.rateFor("CAR"), config.getPeakWindow()));
    strategies.push_back(std::make_unique<FlatRateFeeStrategy>(1.0));

    const ParkingFeeStrategy& peak = *strategies[0];
    const ParkingFeeStrategy& flat = *strategies[1];
    CHECK_EQ(peak.getName(), std::string("peak-hour"));
    CHECK_EQ(flat.getName(), std::string("flat-rate"));
    CHECK_NEAR(peak.calculateFee(entry, exit).totalAmount, 60 * 0.67 + 60 * 0.80);
    CHECK_NEAR(flat.calculateFee(entry, exit).totalAmount, 120.0);  // original CSV app: Rs 1/min
}

TEST_CASE(factory_selects_strategy_from_config_and_vehicle_type) {
    testing::TempDir dir;
    const std::string path = dir.file("flat.cfg");
    {
        std::ofstream out(path);
        out << "fee_strategy = flat\nflat_rate_per_minute = 2.5\n";
    }
    const auto flat = createFeeStrategy(AppConfig::loadFromFile(path), "CAR");
    CHECK(dynamic_cast<FlatRateFeeStrategy*>(flat.get()) != nullptr);

    const auto peak = createFeeStrategy(AppConfig::defaults(), "CAR");
    CHECK(dynamic_cast<PeakHourFeeStrategy*>(peak.get()) != nullptr);
    CHECK_THROWS_AS(createFeeStrategy(AppConfig::defaults(), "TRUCK"), ValidationException);
}

TEST_CASE(parking_lot_prices_each_vehicle_with_its_category_tariff) {
    ParkingLot lot("Lot", {ParkingSlot(1, "1", 'A', 1, "STANDARD"), ParkingSlot(2, "2", 'A', 1, "STANDARD")},
                   AppConfig::defaults());
    const TimePoint entry = timeutil::makeLocal(2026, 10, 21, 10, 0, 0);
    lot.parkVehicle(lot.registerVehicle("MH12AB1234", "CAR"), entry);
    lot.parkVehicle(lot.registerVehicle("MH01EF9012", "BIKE"), entry);
    const auto car = lot.removeVehicle("MH12AB1234", entry + seconds(100), PaymentMethod::Cash);
    const auto bike = lot.removeVehicle("MH01EF9012", entry + seconds(100), PaymentMethod::Cash);
    CHECK_NEAR(car.getFee()->totalAmount, 100 * 0.67);
    CHECK_NEAR(bike.getFee()->totalAmount, 100 * 0.40);  // pricing_rules BIKE row
    CHECK_NEAR(car.getPayment()->getAmount(), car.getFee()->totalAmount);
}

TEST_CASE(config_file_overrides_and_validation) {
    testing::TempDir dir;
    const std::string good = dir.file("good.cfg");
    {
        std::ofstream out(good);
        out << "\xEF\xBB\xBF# comment\nrate.CAR = 1.00 2.00\npeak_start_hour = 9\npeak_end_hour = 10\n"
               "slots = 1-3 Z 4 LARGE\n";
    }
    const AppConfig config = AppConfig::loadFromFile(good);
    CHECK_NEAR(config.rateFor("CAR").peakRate, 2.0);
    CHECK_NEAR(config.rateFor("BIKE").baseRate, 0.40);  // untouched default
    CHECK_EQ(config.getPeakWindow().startHour, 9);
    CHECK_EQ(config.buildSlots().size(), std::size_t(3));
    CHECK_EQ(config.buildSlots()[0].getZone(), 'Z');

    const std::string unknownKey = dir.file("typo.cfg");
    {
        std::ofstream out(unknownKey);
        out << "peak_strat_hour = 9\n";
    }
    CHECK_THROWS_AS(AppConfig::loadFromFile(unknownKey), ValidationException);

    const std::string badRange = dir.file("range.cfg");
    {
        std::ofstream out(badRange);
        out << "peak_start_hour = 30\n";
    }
    CHECK_THROWS_AS(AppConfig::loadFromFile(badRange), ValidationException);
    CHECK_THROWS_AS(AppConfig::loadFromFile(dir.file("missing.cfg")), StorageException);

    // The default layout mirrors database/seed.sql (30 slots, zones A-D).
    const auto slots = AppConfig::defaults().buildSlots();
    CHECK_EQ(slots.size(), std::size_t(30));
    CHECK_EQ(slots[12].getZone(), 'B');
    CHECK_EQ(slots[29].getSlotType(), std::string("LARGE"));
}
