#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <memory>
#include <string>
#include <windows.h>
#include "sl_lidar.h"
#include "sl_lidar_driver.h"

// Original adapter using the SLAMTEC SDK. One JSON object per scan on stdout.
static int fail(const char* stage, sl_result result) {
    std::printf("{\"type\":\"error\",\"message\":\"%s (SDK 0x%08x)\"}\n", stage, (unsigned)result);
    std::fflush(stdout);
    return 1;
}
static bool stopRequested() {
    DWORD available = 0;
    HANDLE input = GetStdHandle(STD_INPUT_HANDLE);
    if (!PeekNamedPipe(input, nullptr, 0, nullptr, &available, nullptr)) return true;
    return available > 0;
}
int main(int argc, char** argv) {
    if (argc != 4) return fail("Expected transport, address and port/baud", 0);
    const std::string transport(argv[1]);
    const int port = std::atoi(argv[3]);
    sl::Result<sl::IChannel*> result = transport == "tcp" ? sl::createTcpChannel(argv[2], port)
        : transport == "udp" ? sl::createUdpChannel(argv[2], port)
        : sl::createSerialPortChannel(argv[2], port);
    if (!result) return fail("Cannot create channel", result.err);
    std::unique_ptr<sl::IChannel> channel(*result);
    auto driverResult = sl::createLidarDriver();
    if (!driverResult) return fail("Cannot create driver", driverResult.err);
    std::unique_ptr<sl::ILidarDriver> driver(*driverResult);
    auto status = driver->connect(channel.get());
    if (SL_IS_FAIL(status)) return fail("Cannot open sensor connection", status);
    sl_lidar_response_device_info_t info{};
    status = driver->getDeviceInfo(info, 3000);
    if (SL_IS_FAIL(status)) return fail("Sensor did not answer. Check address, port and transport", status);
    sl_lidar_response_device_health_t health{};
    status = driver->getHealth(health, 3000);
    if (SL_IS_FAIL(status) || health.status == SL_LIDAR_STATUS_ERROR)
        return fail("Sensor health check failed", status);
    driver->setMotorSpeed();
    status = driver->startScan(false, true);
    if (SL_IS_FAIL(status)) { driver->setMotorSpeed(0); return fail("Cannot start scan", status); }
    std::printf("{\"type\":\"device\",\"model\":%u,\"firmware\":\"%u.%02u\"}\n", info.model, info.firmware_version >> 8, info.firmware_version & 255);
    std::fflush(stdout);
    int missed = 0;
    while (!stopRequested()) {
        sl_lidar_response_measurement_node_hq_t nodes[8192];
        size_t count = 8192;
        status = driver->grabScanDataHq(nodes, count, 1000);
        if (SL_IS_FAIL(status)) {
            if (++missed >= 5) { fail("No scan received for five seconds", status); break; }
            continue;
        }
        missed = 0;
        driver->ascendScanData(nodes, count);
        std::printf("{\"type\":\"scan\",\"points\":[");
        bool first = true;
        for (size_t i = 0; i < count; ++i) {
            const auto& n = nodes[i];
            if (!n.dist_mm_q2 || !n.quality) continue;
            std::printf("%s[%.4f,%.2f,%u]", first ? "" : ",", n.angle_z_q14 * 90.0 / 16384.0, n.dist_mm_q2 / 4.0, n.quality >> 2);
            first = false;
        }
        std::puts("]}"); std::fflush(stdout);
    }
    driver->stop();
    driver->setMotorSpeed(0);
    driver->disconnect();
    return missed >= 5 ? 1 : 0;
}
