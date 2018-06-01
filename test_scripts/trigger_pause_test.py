#!/usr/bin/python
import serial
import argparse
import time

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='USB HUB trigger')
    parser.add_argument('-s','--serial_port', default="/dev/ttyUSB0", type=str,help='serial port device.', nargs='?')
    parser.add_argument('-b','--baudrate', default=115200, type=int, help='baudrate of serial port', nargs='?')
    parser.add_argument('-c','--command', default="AT+STOP", type=str, help='command to send.', nargs='?')
    parser.add_argument('-p','--pausetime', default=30, type=int, help='time to pause.', nargs='?')
    args = parser.parse_args()
    
    ser = serial.Serial(args.serial_port, args.baudrate)
    time.sleep(5)
    ser.write(args.command)
    time.sleep(args.pausetime)
    ser.write("AT+START")
    ser.close()

