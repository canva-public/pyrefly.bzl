"""Shared OTLP trace-output plumbing for wrapper actions."""

def declare_otlp_trace(ctx, args, name):
    """Declare a trace file and add its wrapper argument."""
    output = ctx.actions.declare_file(name + "_otlp_trace.jsonl")
    args.add("--otlp-trace-output")
    args.add(output)
    return output
