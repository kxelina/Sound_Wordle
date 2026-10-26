/* Compile the shared SynthDef for Python's offline renderer.
   Usage: sclang -D engine.scd compile OUTPUT_DIRECTORY
   The renderer sends an OSC score to scsynth -N; no audio device is required. */
(
var directory = PathName(thisProcess.nowExecutingPath).pathOnly;
var args = thisProcess.argv;
if((args.size >= 2) and: { args[0] == "compile" }) {
    try {
        thisProcess.interpreter.executeFile(directory +/+ "synth.scd");
        ~soundDetectiveDefs.do { |definition| definition.writeDefFile(args[1]); };
        "SOUND_DETECTIVE_DEFS_READY".postln;
        0.exit;
    } { |error|
        error.reportError;
        1.exit;
    };
} {
    "Use python -m sound_detective to render a Sound Detective WAV.".postln;
};
)
