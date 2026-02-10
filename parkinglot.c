#include <stdio.h>
#include <string.h>

int main()
{
    int MAX = 50;

    int token[50];
    char numberPlate[50][15];
    int vehicleType[50]; // 1 = Two wheeler, 2 = Four wheeler
    int entryHour[50], entryMinute[50];
    int isActive[50];

    int count = 0;
    int nextToken = 1;
    int choice;

    while (1)
    {
        printf("\n====== SMART PARKING SYSTEM ======\n");
        printf("1. Vehicle Entry\n");
        printf("2. Vehicle Exit\n");
        printf("3. View Active Vehicles\n");
        printf("4. Exit Program\n");
        printf("Enter your choice: ");
        scanf("%d", &choice);

        //  VEHICLE ENTRY
        if (choice == 1)
        {
            if (count >= MAX)
            {
                printf("Parking Full!\n");
                continue;
            }

            token[count] = nextToken++;

            printf("Enter Number Plate: ");
            getchar(); // Clear buffer
            fgets(numberPlate[count], 15, stdin);

        
            numberPlate[count][strcspn(numberPlate[count], "\n")] = 0;

            printf("Select Vehicle Type (1 = Two-wheeler, 2 = Four-wheeler): ");
            scanf("%d", &vehicleType[count]);

            printf("Enter Entry Time (HH MM): ");
            scanf("%d %d", &entryHour[count], &entryMinute[count]);

            isActive[count] = 1;

            printf("\nVehicle Detected by Camera\n");
            printf("Token Generated: %d\n", token[count]);

            count++;
        }

        // VEHICLE EXIT
        else if (choice == 2)
        {
            int exitToken; // Changed from char array to int
            int exitHour, exitMinute;
            int found = 0;

            printf("Enter Token Number at Exit: ");
            scanf("%d", &exitToken); // Read integer

            for (int i = 0; i < count; i++)
            {
            
                if (token[i] == exitToken && isActive[i] == 1)
                {
                    found = 1;

                    printf("Enter Exit Time (HH MM): ");
                    scanf("%d %d", &exitHour, &exitMinute);

                    int entryTime = entryHour[i] * 60 + entryMinute[i];
                    int exitTime = exitHour * 60 + exitMinute;

                    if (exitTime <= entryTime)
                    {
                        printf("Invalid exit time!\n");
                        break;
                    }

                    int totalMinutes = exitTime - entryTime;
                    int totalHours = (totalMinutes + 59) / 60;

                    int baseRate;
                    if (vehicleType[i] == 1)
                        baseRate = 25; // Two-wheeler
                    else
                        baseRate = 40; // Four-wheeler

                    int baseFare = totalHours * baseRate;

                    // Peak Hour Logic (6-9 PM)
                    int peakStart = 18 * 60;
                    int peakEnd = 21 * 60;

                    int overlapStart = (entryTime > peakStart) ? entryTime : peakStart;
                    int overlapEnd = (exitTime < peakEnd) ? exitTime : peakEnd;

                    int peakMinutes = overlapEnd - overlapStart;
                    if (peakMinutes < 0)
                        peakMinutes = 0;

                    int peakHours = (peakMinutes + 59) / 60;
                    int peakFare = peakHours * 10;

                    int totalFare = baseFare + peakFare;

                    printf("\n====== PARKING BILL ======\n");
                    printf("Token Number   : %d\n", token[i]);
                    printf("Number Plate   : %s\n", numberPlate[i]);
                    printf("Vehicle Type   : %s\n",
                           (vehicleType[i] == 1) ? "Two-wheeler" : "Four-wheeler");
                    printf("Parked from %02d:%02d to %02d:%02d\n",
                           entryHour[i], entryMinute[i], exitHour, exitMinute);
                    printf("Total Hours    : %d\n", totalHours);
                    printf("Peak Hours     : %d\n", peakHours);
                    printf("Amount Payable : Rs %d\n", totalFare);

                    isActive[i] = 0;
                    break;
                }
            }

            if (!found)
                printf("Token not found or vehicle already exited!\n");
        }

        // VIEW ACTIVE
        else if (choice == 3)
        {
            int any = 0;
            printf("\nActive Parked Vehicles:\n");
            printf("Token\tPlate\t\tType\tEntry\n");

            for (int i = 0; i < count; i++)
            {
                if (isActive[i] == 1)
                {
                    any = 1;
                    printf("%d\t%s\t\t%s\t%02d:%02d\n",
                           token[i],
                           numberPlate[i],
                           (vehicleType[i] == 1) ? "2W" : "4W",
                           entryHour[i],
                           entryMinute[i]);
                }
            }

            if (!any)
                printf("No vehicles currently parked.\n");
        }

        //  EXIT PROGRAM
        else if (choice == 4)
        {
            printf("System Shutdown. Thank you!\n");
            break;
        }

        else
        {
            printf("Invalid choice! Try again.\n");
        }
    }

    return 0;
}
