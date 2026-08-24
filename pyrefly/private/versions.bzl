"""Registered Pyrefly release artifacts and SHA-256 checksums."""

_RELEASE_URL = "https://github.com/facebook/pyrefly/releases/download/{version}/{asset}"

PYREFLY_PLATFORMS = {
    "linux_aarch64": struct(
        asset = "pyrefly-linux-arm64-musl.tar.gz",
        constraints = [
            "@platforms//cpu:aarch64",
            "@platforms//os:linux",
        ],
    ),
    "linux_x86_64": struct(
        asset = "pyrefly-linux-x86_64-musl.tar.gz",
        constraints = [
            "@platforms//cpu:x86_64",
            "@platforms//os:linux",
        ],
    ),
    "macos_aarch64": struct(
        asset = "pyrefly-macos-arm64.tar.gz",
        constraints = [
            "@platforms//cpu:aarch64",
            "@platforms//os:osx",
        ],
    ),
    "macos_x86_64": struct(
        asset = "pyrefly-macos-x86_64.tar.gz",
        constraints = [
            "@platforms//cpu:x86_64",
            "@platforms//os:osx",
        ],
    ),
}

PYREFLY_RELEASES = {
    "1.3.0-dev.2": {
        "linux_aarch64": "0fb1d18fe63e8249bc75cfdd8ddb3d26f4a376c2ae29f0daa060a7a000ec933d",
        "linux_x86_64": "b3764af4fb8a957aa052fe73d83bd36f33d3b19935adcd9e41828406b8851bea",
        "macos_aarch64": "01ef6cee810ffe6c8484e165c60ead22e723a14ba2733640f33a73ea2dae011c",
        "macos_x86_64": "5bbeb2a089caa05f4064f97419e7b5ecf158fccaddd44b4008a6877ccd0c7a90",
    },
    "1.3.0-dev.1": {
        "linux_aarch64": "2070884128887abdd56cf7b6097f475fa0931b5207efd0da214c6d5481873765",
        "linux_x86_64": "fcaf7a982a36535476f3c5065b5843b5ea5a4d52c812bba1c08a0a56297285ba",
        "macos_aarch64": "4f3ed20b85347aba688f32fb704bb73de27382fe33a0efc60f5c7bca282cea85",
        "macos_x86_64": "7d20ee0b88dd1d3c1a80b7aa466e66af0adb65fa9da6ce2d3052ee0fee03b3ef",
    },
    "1.2.0": {
        "linux_aarch64": "5b27d702c8b8463090fe19ca4e2aa241bf8f2b09daf208feff051a90e4d12cee",
        "linux_x86_64": "18f509653a52fab1aab98d5b776486a4f278c04cc108fec8b52c131785f6d423",
        "macos_aarch64": "312ab21e60fb4385a4cd5ef68bc70e2475d7b541a5cb5a30329db726b2b16e39",
        "macos_x86_64": "f1856386d167696af3fe05b5c2fbe807845e33da1024706cbe979c74ac7d7cdd",
    },
    "1.2.0-dev.3": {
        "linux_aarch64": "baca87cc3aef93f7e1c50bf3e566d7abb4497c43c1d5125b69b9fa8d062eb3b9",
        "linux_x86_64": "0c008a26fc9f3a0eb03c2f9ea0686f74dfafae6cd19157717b927e0c79161dfa",
        "macos_aarch64": "b34fcc6f549d26c0b2d6cfe183c5c4874fa9eddf6f09b7dc0121da15d9f768cd",
        "macos_x86_64": "950be03bee3c30f68dddc057b3823e2b27c5ef75a86fa7bc938059f8dbea49b5",
    },
    "1.2.0-dev.2": {
        "linux_aarch64": "1ccecdf3178056fd915fc2798e30d7f2b7a87590522af8eaf2bb90db4c479761",
        "linux_x86_64": "8889e12d4f3f9369fb168232b768b44bc8d87cf1fc7abdd9431a77952a630e72",
        "macos_aarch64": "7d215272e159164dc75e3fd3fd82d6be2fa17cad827f64b123c73f99ef68f0b3",
        "macos_x86_64": "78418180a3dc9188686dc52d94b2fe488a85aadc8d1f434834ca6d1a5cbf5682",
    },
    "1.2.0-dev.1": {
        "linux_aarch64": "1b86e198fa708e98d322f8ea0c1c79fa5aa17374652f61cef18771204226411a",
        "linux_x86_64": "23df47f9402e2dbcf67dfbad6b5b96792d6c0148d22c00edc5616eccdeaa4ab8",
        "macos_aarch64": "e74308e48a4e3f386a1af486d8e1099af35b709b64f80bf2027308bed2911c4f",
        "macos_x86_64": "631f3a89212ba69273da36bced2c2e06a8e7a9a6f781867b9759193a897b186b",
    },
    "1.1.1": {
        "linux_aarch64": "f55454ac41ed1c086af1bd3cfbe2c2a25b960e46551df50ce047bc1ccb11fb35",
        "linux_x86_64": "fc591b4b283ceddb81116a8dd5c0e70d4f1a7dd291521c4debe0cd588c7fd74c",
        "macos_aarch64": "022a989d2af4748e4d75a48fed7dbb0cc49f30a4b83745d4e4f742d0920ada70",
        "macos_x86_64": "191c7ee2891d2ab55a05b078c94832266e1dda78a9a0381a95fde13a2a27a38b",
    },
    "1.1.0": {
        "linux_aarch64": "83ee6bfc6cf28bdf0290c9b0b50425cd0eff8d663592c8f360952908dd6030ac",
        "linux_x86_64": "32086864fbc8f51c8de6afe7fe3f33ec78720cda6b48d754379c85afbab05242",
        "macos_aarch64": "b587c88a7e6f030f4c9c886a1e4bf33f098c5d2ccbb324fcfd41f0bb8039079f",
        "macos_x86_64": "1ce148e23b3b48d3ca880c74e999c79d7aa70877ab2ded574fb2cd24e53c0b08",
    },
    "1.1.0-dev.2": {
        "linux_aarch64": "af980aba08fc506125b31bb2159c097263f7a496c4c593a342a747e1d7dfd158",
        "linux_x86_64": "a2c17a70959faaf4d1316003a03345deb95fcd684b8f1291bd45a3b5c833a5ca",
        "macos_aarch64": "91a1198e2750d56035385c51c340b9bb45b33c11c0c9938fd816462a585e070f",
        "macos_x86_64": "82ca69862f2274cdec965fc394d85d310337957cac19a01a8a78e548505da0fb",
    },
}

def get_pyrefly_release(version, platform):
    """Return the download URL and SHA-256 digest for a release artifact."""
    if version not in PYREFLY_RELEASES:
        fail("Unsupported Pyrefly version {}".format(repr(version)))
    if platform not in PYREFLY_PLATFORMS:
        fail("Unsupported Pyrefly platform {}".format(repr(platform)))
    return struct(
        digest = PYREFLY_RELEASES[version][platform],
        url = _RELEASE_URL.format(
            asset = PYREFLY_PLATFORMS[platform].asset,
            version = version,
        ),
    )
