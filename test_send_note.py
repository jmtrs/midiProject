import mido, time, random
out = mido.open_output(next(p for p in mido.get_output_names() if "Surge" in p))

scale = [36, 38, 41, 43, 45, 48]  # base grave
for i in range(32):  # 32 pasos
    note = random.choice(scale)
    vel = random.randint(70, 120)
    out.send(mido.Message('note_on', note=note, velocity=vel))
    time.sleep(0.15)
    out.send(mido.Message('note_off', note=note))
