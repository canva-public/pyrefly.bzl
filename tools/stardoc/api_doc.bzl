load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@stardoc//stardoc:stardoc.bzl", "stardoc")

def _api_doc_impl(
        name,
        input,
        symbol_names,
        deps,
        _docs_combiner,
        **kwargs):
    fragment_names = []
    for symbol in symbol_names:
        fragment_name = "{}.{}".format(name, symbol)
        stardoc(
            name = fragment_name,
            input = input,
            out = "{}.md".format(fragment_name),
            symbol_names = [symbol],
            render_main_repo_name = True,
            deps = deps,
            tags = ["manual"],
            visibility = ["//visibility:private"],
        )
        fragment_names.append(fragment_name)

    filename = "{}.generated.md".format(name)
    run_binary(
        name = name,
        srcs = fragment_names,
        outs = [filename],
        args = ["$(execpath {})".format(filename)] + [
            "$(execpath :{})".format(fname)
            for fname in fragment_names
        ],
        tool = _docs_combiner,
        **kwargs
    )

api_doc = macro(
    implementation = _api_doc_impl,
    inherit_attrs = "common",
    attrs = {
        "input": attr.label(
            allow_single_file = True,
            mandatory = True,
        ),
        "deps": attr.label_list(),
        "symbol_names": attr.string_list(
            allow_empty = False,
            configurable = False,
        ),
        "_docs_combiner": attr.label(
            default = "//tools/stardoc:combine_docs",
            executable = True,
            cfg = "exec",
        ),
    },
)
