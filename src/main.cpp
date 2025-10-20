// XRC Technologies DroneCAN Power Module

#include <Arduino.h>
#include <dronecan.h>
#include <IWatchdog.h>
#include <app.h>
#include <vector>
#include <simple_dronecanmessages.h>

// Calculations:
// 0.1mOhm resistor
// 20k-1k voltage divider
// Vout = Vbatt / 21
// 12-bit ADC (4096 bit resolution)
// INA240A2 --> 50V/V Gain
// Voltage (ADC)= I * 0.0001 * 50 = 3.3/4096
// Voltage (ADC) = 3.3/4096 = V_batt / 21
// Target current: 200A
// These are good starting numbers but actual numbers may vary
// I_batt = 0.0064453125 * V_adc
// V_batt = 0.0169189453125 * V_adc
// 1 / I_batt constant = 155.151515
// 1 / V_batt constant = 59.1053391

#define SHUNT_RESISTANCE 0.0025
#define CURRENT_SCALE_FACTOR 1.623
#define VOLTAGE_SCALE_FACTOR 14.705
#define CURRENT_PIN PA2
#define VOLTAGE_PIN PA3

float current;
float voltage;

std::vector<DroneCAN::parameter> custom_parameters = {
    {"NODEID", UAVCAN_PROTOCOL_PARAM_VALUE_INTEGER_VALUE, 127, 0, 127}};

DroneCAN dronecan;

uint32_t looptime = 0;

static void onTransferReceived(CanardInstance *ins, CanardRxTransfer *transfer)
{
    DroneCANonTransferReceived(dronecan, ins, transfer);
}

static bool shouldAcceptTransfer(const CanardInstance *ins,
                                 uint64_t *out_data_type_signature,
                                 uint16_t data_type_id,
                                 CanardTransferType transfer_type,
                                 uint8_t source_node_id)

{
    return false || DroneCANshoudlAcceptTransfer(ins, out_data_type_signature, data_type_id, transfer_type, source_node_id);
}

void setup()
{
    app_setup();
    IWatchdog.begin(2000000); 
    Serial.begin(115200);
    dronecan.version_major = 1;
    dronecan.version_minor = 0;
    dronecan.init(
        onTransferReceived, 
        shouldAcceptTransfer, 
        custom_parameters,
        "XRC Technologies Power Module"
    );
    pinMode(CURRENT_PIN, INPUT);
    pinMode(VOLTAGE_PIN, INPUT);

    while (true)
    {
        const uint32_t now = millis();

        // send our battery message at 10Hz
        if (now - looptime > 100)
        {
            looptime = millis();

            // construct dronecan packet
            current = analogRead(CURRENT_PIN) / CURRENT_SCALE_FACTOR;
            voltage = analogRead(VOLTAGE_PIN) / VOLTAGE_SCALE_FACTOR;
            uavcan_equipment_power_BatteryInfo pkt{};
            pkt.voltage = voltage;
            pkt.current = current;
            //pkt.temperature = INA.getTemperature();

            sendUavcanMsg(dronecan.canard, pkt);
        }

        dronecan.cycle();
        IWatchdog.reload();
    }
}

void loop()
{
    // Doesn't work coming from bootloader ? use while loop in setup
}
