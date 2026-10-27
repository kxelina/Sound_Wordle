/* Original instrument models, isolated from the scored challenge synthesizer.
   No samples. Compile with: sclang -D composition.scd OUTPUT_DIRECTORY */
(
var definition;
definition = SynthDef(\sdCompositionVoice, {
    |out=16, instrument=0, freq=261.6256, noteOff=0.6, velocity=1, seed=2026,
    h1=1,h2=0,h3=0,h4=0,h5=0,h6=0,h7=0,h8=0,
    attack=0.03,decay=0.18,sustain=0.65,release=0.25|
    var age,held,a,d,r,envelope,amps,ks,frequencies,plain,piano,violin,guitar;
    var vibrato,bowed,pick,string,brightness,tone,lifetime;
    RandSeed.ir(1,seed);
    age = Sweep.ar(0,1); held = age.min(noteOff);
    a=attack.max(0.001); d=decay.max(0.001); r=release.max(0.001);
    envelope=(held/a).clip(0,1) * (1-(((held-a)/d).clip(0,1)*(1-sustain))) *
        (1-((age-noteOff)/r).clip(0,1));
    ks=(1..8); frequencies=ks*freq;
    amps=[h1,h2,h3,h4,h5,h6,h7,h8].clip(0,1) * (frequencies < (SampleRate.ir*0.5));
    amps=amps/amps.sum.max(0.000001);
    plain=Mix(SinOsc.ar(frequencies,0,amps));
    // Higher piano partials fade faster, with mild string inharmonicity.
    piano=Mix(SinOsc.ar(frequencies*((1+(ks.squared*0.00004)).sqrt),0,
        amps * exp(age.neg/(0.25+(decay*7)/(ks.sqrt)))));
    pick=HPF.ar(PinkNoise.ar,1200)*exp(age.neg/0.012);
    piano=piano+(pick*0.035);
    // Bowed harmonics sustain, with a gradual vibrato and a little bow noise.
    vibrato=1+(SinOsc.kr(5.4,0,0.004)*(age/0.35).clip(0,1));
    bowed=Mix(SinOsc.ar(frequencies*vibrato,0,amps));
    violin=bowed+(BPF.ar(PinkNoise.ar,1800,0.6)*0.025);
    // Karplus–Strong excitation and body partials for the plucked string.
    brightness=(amps*ks).sum.linlin(1,8,0.78,0.05).clip(0.05,0.85);
    string=Pluck.ar(PinkNoise.ar*0.8,1,0.025,freq.reciprocal,0.5+(decay*6),brightness);
    guitar=(string*0.8)+(plain*exp(age.neg/(0.3+(decay*3)))*0.2)+(pick*0.015);
    tone=Select.ar(instrument.clip(0,3),[plain,piano,violin,guitar]);
    lifetime=EnvGen.ar(Env([1,1,0],[noteOff+r,0.01],\lin),doneAction:2);
    OffsetOut.ar(out,LeakDC.ar(tone)*envelope*lifetime*0.20*velocity);
});
definition.writeDefFile(thisProcess.argv[0]);
"SOUND_DETECTIVE_INSTRUMENT_READY".postln;
0.exit;
)
