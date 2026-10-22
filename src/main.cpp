// Entry point of parkinglot.exe - the C++ core of the Smart Parking
// Management System. All behaviour lives in CommandLineApp and the classes it
// uses; main() only forwards the arguments.

#include <iostream>
#include <string>
#include <vector>

#include "app/CommandLineApp.hpp"

int main(int argc, char* argv[]) {
    const std::vector<std::string> args(argv + 1, argv + argc);
    parking::CommandLineApp app(std::cout, std::cerr);
    return app.run(args);
}
