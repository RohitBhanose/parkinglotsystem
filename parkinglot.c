#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

int is_peak(int hour, int weekday)
{
    // Weekend OR 6PM–10PM
    if (weekday == 0 || weekday == 6) return 1;
    if (hour >= 18 && hour < 22) return 1;
    return 0;
}

int main(int argc, char *argv[])
{
    if (argc < 3)
    {
        printf("ERROR=Invalid input\n");
        return 1;
    }

    long entry = atol(argv[1]);
    long exit = atol(argv[2]);

    if (exit <= entry)
    {
        printf("ERROR=Invalid time\n");
        return 1;
    }

    // CANCEL FEATURE
    if (argc >= 4 && strcmp(argv[3], "cancel") == 0)
    {
        printf("STATUS=CANCELLED\n");
        printf("AMOUNT=0\n");
        return 0;
    }

    // 🔥 1 second = 1 minute
    int total_minutes = (int)(exit - entry);
    if (total_minutes <= 0) total_minutes = 1;

    float base_rate = 0.67;
    float peak_surcharge = 0.8;

    int base_minutes = 0;
    int peak_minutes = 0;

    // 🔥 LOOP THROUGH EACH "MINUTE"
    for (long t = entry; t < exit; t++)
    {
        struct tm *tm_info = localtime(&t);

        int hour = tm_info->tm_hour;
        int weekday = tm_info->tm_wday;

        if (is_peak(hour, weekday))
            peak_minutes++;
        else
            base_minutes++;
    }

    float base_amount = base_minutes * base_rate;
    float peak_amount = peak_minutes * peak_surcharge;

    float total = base_amount + peak_amount;

    // 🔥 OUTPUT FULL BREAKDOWN
    printf("STATUS=ACTIVE\n");
    printf("TOTAL_DURATION=%d\n", total_minutes);

    printf("BASE_MINUTES=%d\n", base_minutes);
    printf("BASE_RATE=%.2f\n", base_rate);
    printf("BASE_AMOUNT=%.2f\n", base_amount);

    printf("PEAK_MINUTES=%d\n", peak_minutes);
    printf("PEAK_SURCHARGE=%.2f\n", peak_surcharge);
    printf("PEAK_AMOUNT=%.2f\n", peak_amount);

    printf("TOTAL_AMOUNT=%.2f\n", total);

    return 0;
}