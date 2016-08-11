import themis


def setup_robot(roboRIO: themis.frc.RoboRIO):
    joy1 = roboRIO.driver_station.joystick(1)
    ctrl_left_yaxis = -joy1.axis(2)
    ctrl_right_yaxis = -joy1.axis(6)

    left_motors = roboRIO.pwm.talon_sr(1)
    right_motors = - roboRIO.pwm.talon_sr(2)

    ball_sensor = roboRIO.gpio.input(1, interrupt=True)

    themis.drive.tank_drive(ctrl_left_yaxis, ctrl_right_yaxis, left_motors, right_motors)

    def autonomous_main(act):
        act.set(left_motors, 0.5)
        act.set(right_motors, 0.5)
        act.wait_ms(500)
        act.wait_until(ball_sensor)
        act.set(left_motors, 0.0)
        act.set(right_motors, 0.0)

    roboRIO.run_during_auto(autonomous_main)


themis.frc.robot(1540, setup_robot)
