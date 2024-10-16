for i in range(NUM_CHANNELS):
    v1_target = -1
    v2_target = 2
    dac_code1 = (v1_target / 8) * DEFAULT_SCALE + DEFAULT_OFFSET
    dac_code2 = (v2_target / 8) * DEFAULT_SCALE + DEFAULT_OFFSET
    v1_dac_code = ((dac_code1 - DEFAULT_OFFSET) / (neg_one_volts[i] / 8)) * (
        v1_target / 8
    ) + DEFAULT_OFFSET
    v2_dac_code = ((dac_code2 - DEFAULT_OFFSET) / (two_point_five_volts[i] / 8)) * (
        v2_target / 8
    ) + DEFAULT_OFFSET

    scale = (v2_dac_code - v1_dac_code)/((v2_target - v1_target) / 8)
    offset = v1_dac_code - ((v1_target/8) * scale)
