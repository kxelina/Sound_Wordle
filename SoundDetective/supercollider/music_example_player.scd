/* Developer examples only: recorded mono buffer -> existing shared effects.
   This adds no recording-import UI or playable music-case rules. */
(
var directory = PathName(thisProcess.nowExecutingPath).pathOnly;
var args = thisProcess.argv;
if((args.size >= 2) and: { args[0] == "compile" }) {
    try {
        thisProcess.interpreter.executeFile(directory +/+ "synth.scd");
        ~soundDetectiveEffectsDef.writeDefFile(args[1]);
        SynthDef(\soundDetectiveExamplePlayer, { |out=16, bufnum=0, rateFactor=1|
            // Music puzzles keep the source in forward chronological order.
            Out.ar(out, PlayBuf.ar(1, bufnum,
                BufRateScale.kr(bufnum) * rateFactor.clip(0.65, 1.35), doneAction:2));
        }).writeDefFile(args[1]);
        "SOUND_DETECTIVE_MUSIC_EXAMPLES_READY".postln;
        0.exit;
    } { |error|
        error.reportError;
        1.exit;
    };
} {
    "Use python -m sound_detective.render_music_examples".postln;
    1.exit;
};
)
