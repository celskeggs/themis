import themis.channel


def tank_drive(left_in: themis.channel.FloatInput, right_in: themis.channel.FloatInput,
               left_out: themis.channel.FloatOutput, right_out: themis.channel.FloatOutput):
    left_in.send(left_out)
    right_in.send(right_out)
