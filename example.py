import themis


def setup_robot(roboRIO: themis.frc.RoboRIO):
    print("I only happen once!")

    joy1 = roboRIO.driver_station.joystick(1).deadzone(0.1)
    ctrl_left_yaxis = joy1.axis(2) * -1
    ctrl_right_yaxis = joy1.axis(6) * -1

    ctrl_button = joy1.button(1)

    joy2 = roboRIO.driver_station.joystick(2).deadzone(0.1)
    aux_x_axis = joy2.axis(1) * 0.5
    aux_y_axis = joy2.axis(2)
    aux_trigger = joy2.button(1)
    aux_button = joy2.button(3)
    aux_button_6 = joy2.button(6)

    left_motors = roboRIO.talon_sr(4) - roboRIO.talon_sr(5) + roboRIO.talon_sr(6)
    right_motors = - roboRIO.talon_sr(1) - roboRIO.talon_sr(2) - roboRIO.talon_sr(3)
    shooter_intake = roboRIO.talon_sr(8) * -1
    shooter_left = roboRIO.can.talon_simple(9) * -1
    shooter_right = roboRIO.can.talon_simple(8)
    shooter = shooter_left + shooter_right

    shifter = roboRIO.can.pcm.solenoid(1)
    ball_sensor = roboRIO.gpio.input(1, interrupt=True)

    shifting_state = themis.Boolean(value=True)
    shifting_state.control(shifter)
    shifting_state.toggle_when(ctrl_button.press)

    themis.drive.tank_drive(ctrl_left_yaxis, ctrl_right_yaxis,
                            left_motors, right_motors)

    contains_ball = themis.Boolean(value=False)
    contains_ball.set_true_when(ball_sensor.release)
    contains_ball.set_false_when(aux_trigger.press)
    contains_ball.set_false_when(aux_button.press)

    aiming = themis.Boolean(value=False)
    aiming.toggle_when(aux_button_6.press)
    (aux_x_axis * aux_y_axis * aiming.choose(0, 1) - aux_y_axis) * aux_trigger.choose(0, 1).with_ramping(0.5).control(
        shooter_right)
    (- aux_x_axis * aux_y_axis * aiming.choose(0, 1) - aux_y_axis) * aux_trigger.choose(0, 1).with_ramping(0.5).control(
        shooter_left)

    def turn(act, degrees):
        act.set(left_motors, 1.0)
        act.set(right_motors, -1.0)
        act.wait_ms(3.70 * degrees)
        act.set(left_motors, 0)
        act.set(right_motors, 0)

    def shoot(act):
        act.set(shooter, 1.0)
        act.wait_ms(500)
        act.set(shooter_intake, 1.0)
        act.wait_ms(1500)
        act.set(shooter, 0.0)
        act.set(shooter_intake, 0.0)

    def stop(act):
        act.set(left_motors, 0.0)
        act.set(right_motors, 0.0)
        act.set(shooter_intake, 0.0)
        act.set(shooter, 0.0)

    def autonomous_main(act):
        act.set(shooter_intake, 1.0)
        turn(act, 70)
        act.set(left_motors, -0.25)
        act.set(right_motors, -0.25)
        act.wait_ms(200)
        act.wait_until(ball_sensor)
        act.set(shooter_intake, 0.0)
        act.set(left_motors, 1.0)
        act.set(right_motors, 0.9)
        act.wait_ms(1000)
        stop(act)
        shoot(act)
        act.set(left_motors, 1.0)
        act.set(right_motors, 0.9)
        act.set(shooter_intake, 1.0)
        act.wait_ms(200)
        stop(act)

    roboRIO.run_during_auto(autonomous_main)


themis.frc.robot(1540, setup_robot)
