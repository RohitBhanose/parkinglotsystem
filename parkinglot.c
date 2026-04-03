#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(int argc, char *argv[])
{
    // ---------------- INPUT CHECK ----------------
    if (argc < 3)
    {
        printf("Invalid input\n");
        return 0;
    }

    // ---------------- GET TIMES ----------------
    long entry = atol(argv[1]);
    long exit = atol(argv[2]);

    if (exit <= entry)
    {
        printf("Invalid time\n");
        return 0;
    }

    // ---------------- DURATION ----------------
    int duration = exit - entry;  // seconds

    // Demo logic: 1 sec = 1 unit (for quick demo)
    int billable_time = duration;

    // ---------------- TIME INFO ----------------
    time_t now = time(NULL);
    struct tm *t = localtime(&now);

    int hour = t->tm_hour;
    int weekday = t->tm_wday; // 0 = Sunday, 6 = Saturday

    float rate;

    // ---------------- RATE LOGIC ----------------
    // Weekend OR rush hours (6–10 PM)
    if (weekday == 0 || weekday == 6 || (hour >= 18 && hour < 22))
    {
        rate = 1.0;   // ₹1 per unit
    }
    else
    {
        rate = 0.66;  // ₹0.66 per unit
    }

    // ---------------- BILL ----------------
    float amount = billable_time * rate;

    // ---------------- OUTPUT ----------------
    printf("\n===== BILL =====\n");
    printf("Duration: %d units\n", billable_time);
    printf("Rate: %.2f Rs/unit\n", rate);
    printf("Amount: Rs %.2f\n", amount);

    return 0;
}