/* Shared DSP for single notes and complete phrases. No audio device is booted. */
(
var voiceGraph, effectsGraph, endingGraph;

voiceGraph = { |partials, attack, decay, sustain, release, freq, noteOff, velocity|
    var harmonics, tone, envelope;
    var a, d, s, r, mix, age, heldAge, off, frequencies;
    var attackRamp, decayRamp, releaseRamp;

    harmonics = partials.clip(0,1);
    frequencies = (1..8) * freq.max(1);
    // Exclude partials at/above Nyquist; never fold them into another pitch.
    harmonics = harmonics * (frequencies < (SampleRate.ir * 0.5));
    a = attack.clip(0.01,0.40); d = decay.clip(0.02,0.60);
    s = sustain.clip(0,1); r = release.clip(0.02,1.20);

    // Preserve harmonic ratios and fixed zero phases, with gain headroom.
    tone = Mix(SinOsc.ar(frequencies.min(SampleRate.ir * 0.5), 0, harmonics));
    tone = tone / harmonics.sum.max(0.000001) * 0.20 * velocity.clip(0,1);
    // Integer sample count avoids accumulated ramp error and makes S=0 silent.
    // Freeze the attack/decay level at key release, including very short notes.
    age = Phasor.ar(0, 1, 0, SampleRate.ir * 60) * SampleDur.ir;
    off = noteOff.max(SampleDur.ir);
    heldAge = age.min(off);
    attackRamp = (heldAge / a).clip(0,1);
    decayRamp = 1 - (((heldAge - a) / d).clip(0,1) * (1 - s));
    releaseRamp = 1 - (((age - off) / r).clip(0,1));
    envelope = attackRamp * decayRamp * releaseRamp;
    tone * envelope;
};

effectsGraph = { |tone, filterMode, cutoff, rq, delayOn, delayTime, delayDecay,
    delayMix, reverbOn, room, damping, reverbMix, filterRepair=0|
    var filtered, echo, delayed, stereo, wet, mix;
    filtered = Select.ar(filterMode.clip(0,2), [
        tone,
        RLPF.ar(tone, cutoff.clip(120,4000), rq.clip(0.25,1.41421356)),
        RHPF.ar(tone, cutoff.clip(120,4000), rq.clip(0.25,1.41421356))
    ]);
    // Music repair only: recover the known dry source before the other damage.
    // Default zero leaves every ordinary synthesizer/effects path unchanged.
    filtered = (filtered * (1-filterRepair.clip(0,1))) + (tone * filterRepair.clip(0,1));
    // CombC supplies delayed echoes; decayTime is time to decay by 60 dB.
    echo = CombC.ar(filtered, 0.60, delayTime.clip(0.08,0.60), delayDecay.clip(0.20,3.0));
    mix = delayMix.clip(0,0.50);
    // SC binary operators have equal precedence: group both mix terms.
    delayed = Select.ar(delayOn.clip(0,1), [filtered, (filtered*(1-mix)) + (echo*mix)]);

    stereo = delayed ! 2;
    wet = FreeVerb2.ar(delayed, delayed, reverbMix.clip(0,0.50), room.clip(0,0.85), damping.clip(0,1));
    Select.ar(reverbOn.clip(0,1), [stereo,wet]);
};

endingGraph = { |duration|
    // Do not free the effects at note-off. Only fade the final 20 ms.
    EnvGen.ar(Env.linen(0, duration.max(0.02)-0.02, 0.02, 1, \lin), doneAction:2);
};

// Keep the original one-note graph and controls for API compatibility.
~soundDetectiveDef = SynthDef(\soundDetective, {
    |out=0, h1=1, h2=0, h3=0, h4=0, h5=0, h6=0, h7=0, h8=0,
    attack=0.03, decay=0.18, sustain=0.65, release=0.25,
    freq=220, noteOff=1.20, velocity=1,
    filterMode=0, cutoff=1200, rq=1.41421356,
    delayOn=0, delayTime=0.25, delayDecay=0.8, delayMix=0.25,
    reverbOn=0, room=0.5, damping=0.5, reverbMix=0.2, duration=2.6|
    var tone, stereo;
    tone = voiceGraph.value([h1,h2,h3,h4,h5,h6,h7,h8],
        attack, decay, sustain, release, freq, noteOff, velocity);
    stereo = effectsGraph.value(tone, filterMode, cutoff, rq,
        delayOn, delayTime, delayDecay, delayMix, reverbOn, room, damping, reverbMix);
    OffsetOut.ar(out, stereo * endingGraph.value(duration));
});

~soundDetectiveVoiceDef = SynthDef(\soundDetectiveVoice, {
    |out=16, h1=1, h2=0, h3=0, h4=0, h5=0, h6=0, h7=0, h8=0,
    attack=0.03, decay=0.18, sustain=0.65, release=0.25,
    freq=220, noteOff=1.20, velocity=1|
    var tone, lifetime;
    tone = voiceGraph.value([h1,h2,h3,h4,h5,h6,h7,h8],
        attack, decay, sustain, release, freq, noteOff, velocity);
    // The voice is already silent at the end of Release; then free its node.
    lifetime = EnvGen.ar(Env([1,1,0],
        [noteOff.max(SampleDur.ir) + release.clip(0.02,1.20), 0.01], \lin), doneAction:2);
    OffsetOut.ar(out, tone * lifetime);
});

~soundDetectiveEffectsDef = SynthDef(\soundDetectiveEffects, {
    |in=16, out=0, filterMode=0, cutoff=1200, rq=1.41421356,
    delayOn=0, delayTime=0.25, delayDecay=0.8, delayMix=0.25,
    reverbOn=0, room=0.5, damping=0.5, reverbMix=0.2, duration=2.6, filterRepair=0|
    var stereo;
    stereo = effectsGraph.value(In.ar(in,1), filterMode, cutoff, rq,
        delayOn, delayTime, delayDecay, delayMix, reverbOn, room, damping, reverbMix, filterRepair);
    // Source OffsetOut supplies exact onset offsets; do not offset effects again.
    Out.ar(out, stereo * endingGraph.value(duration));
});

// Procedural category sources. Python schedules the events; no samples or
// network assets are used. RandSeed keeps every audition/export repeatable.
~sdRainBed = SynthDef(\sdRainBed, { |out=0, seed=2026, cutoff=2600, amp=0.07, variation=0.25, duration=3.6|
    var noise, movement, ending;
    RandSeed.ir(1, seed);
    noise = HPF.ar(LPF.ar((WhiteNoise.ar * 0.65) + (PinkNoise.ar * 0.35), cutoff.clip(500,10000)), 90);
    movement = 1 + (LFNoise1.kr(1.3) * variation.clip(0,1) * 0.85);
    ending = EnvGen.ar(Env.linen(0.04, duration-0.10, 0.06), doneAction:2);
    OffsetOut.ar(out, (noise * movement * amp * ending) ! 2);
});
~sdDrop = SynthDef(\sdDrop, { |out=0, seed=2026, cutoff=2600, length=0.045, amp=0.12, resonance=0.3|
    var envelope, noise, drop;
    RandSeed.ir(1, seed);
    envelope = EnvGen.ar(Env.perc(0.001, length.max(0.002), 1, -5), doneAction:2);
    noise = WhiteNoise.ar;
    drop = (LPF.ar(noise, cutoff.clip(500,10000)) * 0.65) +
        (BPF.ar(noise, (cutoff*0.55).clip(200,9000), resonance.clip(0.1,1)) * 0.35);
    OffsetOut.ar(out, (drop * envelope * amp) ! 2);
});
~sdChirp = SynthDef(\sdChirp, { |out=0, seed=2026, freq=1174, sweep=7, length=0.18, brightness=0.2|
    var position, frequency, tone, envelope;
    position = Line.ar(0, 1, length.max(0.01));
    frequency = freq * ((position-0.5) * sweep.clip(-12,12)).midiratio;
    tone = SinOsc.ar(frequency) + (SinOsc.ar(frequency*2) * brightness * 0.5) +
        (SinOsc.ar(frequency*3) * brightness * 0.25);
    envelope = EnvGen.ar(Env.sine(length.max(0.01)), doneAction:2);
    OffsetOut.ar(out, (tone * envelope * 0.16 / (1+(brightness*0.75))) ! 2);
});
~sdPluck = SynthDef(\sdPluck, { |out=0, seed=2026, freq=261, decay=0.7, brightness=0.5, body=0.3, noise=0.12, duration=3.44|
    var excitation, string, bodyTone, pick, end;
    RandSeed.ir(1, seed);
    excitation = PinkNoise.ar * EnvGen.ar(Env.perc(0.001,0.018));
    string = Pluck.ar(excitation, 1, 0.02, freq.reciprocal, decay.clip(0.15,2), 0.9-(brightness*0.85));
    bodyTone = SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.003,decay,1,-6.9));
    pick = HPF.ar(WhiteNoise.ar, 1500) * EnvGen.ar(Env.perc(0.001,0.025)) * noise;
    end = EnvGen.ar(Env.linen(0, duration-0.04,0.04), doneAction:2);
    OffsetOut.ar(out, (((string*(1-body)) + (bodyTone*body*0.5) + (pick*0.4)) * end * 0.24) ! 2);
});
~sdRadio = SynthDef(\sdRadio, { |out=0, seed=2026, cutoff=6500, colour=0.2, flutter=0.65, rate=8, duration=3.6|
    var noise, modulation, end;
    RandSeed.ir(1, seed);
    noise = (WhiteNoise.ar*(1-colour)) + (PinkNoise.ar*colour);
    modulation = 1 - (flutter*0.5) + (SinOsc.ar(rate, -pi/2)*flutter*0.5);
    end = EnvGen.ar(Env.linen(0.03, duration-0.09,0.06), doneAction:2);
    OffsetOut.ar(out, (HPF.ar(LPF.ar(noise,cutoff.clip(500,10000)),80) * modulation * end * 0.15) ! 2);
});

~soundDetectiveDefs = [~soundDetectiveDef, ~soundDetectiveVoiceDef, ~soundDetectiveEffectsDef,
    ~sdRainBed, ~sdDrop, ~sdChirp, ~sdPluck, ~sdRadio];
)
