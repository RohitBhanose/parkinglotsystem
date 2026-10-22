# OOP Viva Guide: Smart Parking (C++ core)

A cheat sheet for the OOPL viva: each concept in one or two plain sentences, and the exact file and method to open.

**Before the viva:** run `build.bat test`, then `build\parkinglot.exe demo`. The demo prints ten numbered sections that match the list below and uses the real classes. It needs no camera, no database and no model download.

---

## 1. Classes and objects

**Idea:** a class is a blueprint (data + functions); an object is one real thing made from it.

**Show:** [`src/app/DemoRunner.cpp`](src/app/DemoRunner.cpp), `DemoRunner::run()`, sections 1–2. A `ParkingLot` object creates `Vehicle` objects and parks them, which creates `ParkingTransaction` objects that occupy `ParkingSlot` objects. Each class has its own `.hpp` (declaration) and `.cpp` (implementation).

**Say:** "Each real-world thing in a parking lot is its own class: vehicle, slot, transaction, payment, fee policy and the lot itself. They work together only through public methods."

## 2. Encapsulation

**Idea:** keep data private and let it change only through methods that check the rules.

**Show:**
- [`src/models/ParkingSlot.hpp`](src/models/ParkingSlot.hpp): occupancy is private. The only way to change it is `assignVehicle()`, which throws if the slot is occupied, and `releaseVehicle()`, which throws if the wrong session tries to free it ([`ParkingSlot.cpp`](src/models/ParkingSlot.cpp#L16-L35)).
- [`src/models/ParkingTransaction.cpp`](src/models/ParkingTransaction.cpp#L42-L76): `startSession()`, `endSession()` and `cancelTransaction()` all call `requireStatus()` first, so a session cannot be ended twice.
- [`src/models/Payment.cpp`](src/models/Payment.cpp#L42): `processPayment()` is the only way to mark a payment as paid.

**Say:** "There is no `setOccupied(true)` or `setStatus()`. Anything that could break a rule has to go through a checking method."

## 3. Abstraction

**Idea:** show *what* something does and hide *how* it does it.

**Show:**
- [`src/services/ParkingFeeStrategy.hpp`](src/services/ParkingFeeStrategy.hpp#L20): `ParkingFeeStrategy` has pure virtual functions (`= 0`). `ParkingLot` only knows "it can calculate a fee", not which formula is used.
- [`src/storage/ParkingRepository.hpp`](src/storage/ParkingRepository.hpp#L14): `ParkingRepository` only says "load / save transactions". `ParkingRecordManager` does not know whether the data goes to a CSV file or to MySQL.

**Say:** "I can add a new tariff or a new storage type without touching `ParkingLot`."

## 4. Inheritance

**Idea:** a derived class reuses a base class and specialises it ("is-a").

**Show:**
- [`src/models/Vehicle.hpp`](src/models/Vehicle.hpp#L12-L64): `TwoWheeler` and `FourWheeler` inherit from the abstract `Vehicle`. Id, plate and type live only in the base. The derived classes add their wheel count, category name and their own `displayDetails()`. The base constructor is `protected`, so only derived classes can create a `Vehicle`.
- `PeakHourFeeStrategy` and `FlatRateFeeStrategy` inherit `ParkingFeeStrategy`; `CsvParkingRepository` and `MySqlParkingRepository` inherit `ParkingRepository`.
- [`src/exceptions/ParkingException.hpp`](src/exceptions/ParkingException.hpp): `ParkingException` inherits `std::runtime_error`, and six specific exceptions inherit it.

**Demo:** sections 1 and 7. The bike and car show different wheel counts and get different tariffs.

## 5. Polymorphism (runtime)

**Idea:** the same call through a base-class pointer or reference runs the derived class's version, decided at runtime by `virtual`.

**Show:**
- [`src/services/ParkingLot.cpp`](src/services/ParkingLot.cpp#L102-L111), `ParkingLot::removeVehicle()`. It calls `strategyFor(vehicle type)`, which returns a `const ParkingFeeStrategy&` stored as a `std::unique_ptr<ParkingFeeStrategy>`. `endSession()` then calls `calculateFee()`, which calls the virtual `computeFee()`.
- `createFeeStrategy()` at the bottom of [`ParkingFeeStrategy.cpp`](src/services/ParkingFeeStrategy.cpp) picks `PeakHourFeeStrategy` or `FlatRateFeeStrategy` from `config/parking.cfg` (`fee_strategy = peak|flat`).
- `vehicle->displayDetails()` on a `shared_ptr<const Vehicle>` in `DemoRunner::run()`, section 1.

**Demo:** section 8 runs the same `calculateFee()` call through three strategy objects and gets three different answers.

**Say:** "`calculateFee()` is non-virtual and validates the times once. The virtual `computeFee()` is what changes per class."

## 6. Constructors and destructors

**Show:**
- Validating constructors throw if the object would be invalid: [`Vehicle::Vehicle`](src/models/Vehicle.cpp#L11), [`ParkingSlot::ParkingSlot`](src/models/ParkingSlot.cpp#L9), `ParkingTransaction::ParkingTransaction`, and `Payment::Payment`, which uses the template `requireInRange` in its initialiser list.
- Every polymorphic base has a **virtual destructor** (`virtual ~Vehicle() = default;` etc.), so deleting through a base pointer is safe.
- **RAII:** [`src/storage/MySqlParkingRepository.cpp`](src/storage/MySqlParkingRepository.cpp). `PreparedStatement` closes its statement in its destructor, `SqlTransaction` rolls back in its destructor unless `commit()` ran, and the repository's destructor closes the connection. File streams close themselves. There is no manual `new`/`delete` anywhere: only `std::unique_ptr` and `std::shared_ptr`.

## 7. File handling

**Show:** [`src/storage/CsvParkingRepository.cpp`](src/storage/CsvParkingRepository.cpp#L200)

- `readFile()`: `std::ifstream`, header check, row-by-row parsing. Bad rows become warnings and are kept, never deleted. A missing file means "no records yet".
- `writeFile()`: `std::ofstream` to `parking_data.csv.tmp`, then rename over the real file, so a crash cannot leave half a file. Before upgrading an old-format file, it keeps a one-time `.legacy-backup` copy.
- [`src/config/KeyValueFile.cpp`](src/config/KeyValueFile.cpp): reads `config/parking.cfg` and `.env`.

**Demo:** section 6 saves, prints the CSV file, then loads it into a *new* lot object.

## 8. Exception handling

**Show:**
- **throw:** e.g. `ParkingLot::parkVehicle()` throws `SlotUnavailableException` when the lot is full, and `InvalidSessionStateException("ALREADY_PARKED")` for a duplicate entry.
- **catch and translate:** [`CommandLineApp::runCommand()`](src/app/CommandLineApp.cpp#L158) catches `ParkingException&` (the base class) and prints `{"ok":false,"error_code":...}`. Python turns that into `ParkingCoreError`, and Streamlit shows the message.
- **catch, add context, rethrow:** [`ParkingRecordManager::loadTransactions()`](src/services/ParkingRecordManager.cpp#L10) adds the transaction id to a loading error.

**Demo:** section 9 shows full lot, ending a closed session, an exit before entry, a bad plate, and a missing file. Each one is caught and printed with its code.

**Say:** "Plain input checks such as a missing argument are normal `if` checks. Exceptions are for broken rules or failed I/O."

## 9. STL and templates

**STL used for real work:**

| Container / algorithm | Where it is used |
|---|---|
| `std::vector<ParkingSlot>` | the lot's slots |
| `std::unordered_map` | plate → active session, slot number → index, vehicle type → strategy |
| `std::find_if` | finds the first free slot in `ParkingLot::findAvailableSlot()` |
| `std::copy_if`, `std::stable_sort` | build the history in `getParkingHistory()` |
| `std::optional`, `std::chrono` (`TimePoint`), `std::filesystem` | throughout |

**Custom templates:** [`src/util/Validation.hpp`](src/util/Validation.hpp)

- `requireInRange<T>(value, low, high, name)`: one function for `int` hours, `double` rates and payment amounts. Used in `AppConfig::validate()` and `Payment::Payment()`.
- `findOrNull<Map, Key>(map, key)`: returns a pointer or `nullptr` for any map type. Used for every lookup in `ParkingLot` and in `AppConfig::rateFor()`.

**Demo:** section 10. Tests: `require_in_range_template_works_for_several_types` and `find_or_null_template_works_for_map_types` in `tests/test_models.cpp`.

---

## Likely questions

- **Why does the fee strategy take entry and exit times, not hours?** The original rule depends on the clock: peak is weekends or 18:00–22:00. A duration alone cannot tell you how much of the stay was peak.
- **Did the fees change?** No. The C++ output was compared with the original `parkinglot.c` on 3,000 random stays, and the minute splits always matched. The only difference is that C's `float` was sometimes one paisa off on multi-day stays; C++ uses `double`. (Note that 1 real second is billed as 1 "minute", which is a demo setting inherited from the C code.)
- **How does Python talk to C++?** `parking_core.py` runs `build\parkinglot.exe <command>` and reads one JSON line back. The old call `parkinglot.exe <entry> <exit>` still prints the same `KEY=VALUE` output as the C version.
- **Where is the business logic?** In C++ (`src/`). Python handles the camera, YOLO/OCR and the web pages. In MySQL mode, the existing stored procedures also allocate slots (that is the DBMS part of the project); fares still come from C++.
- **Is payment real?** No gateway. `Payment::processPayment()` records that the attendant collected cash or UPI; the QR code is a static image.

## Two-minute live script

1. `build\parkinglot.exe demo`: scroll through sections 1–10.
2. `build\parkinglot.exe entry MH12AB1234 --data demo.csv`, then run the same command again to show the `ALREADY_PARKED` error. Then run `build\parkinglot.exe exit MH12AB1234 --data demo.csv` and `build\parkinglot.exe status --data demo.csv`.
3. Open `ParkingLot::removeVehicle()` to show the polymorphic call, and `ParkingSlot::assignVehicle()` to show encapsulation.
4. `build.bat test`: 31/31 tests pass.
