"""向后兼容：请使用 im_message_params."""

from sensehub.cognition.im_message_params import (  # noqa: F401
    extract_im_send_params,
    resolve_im_message_params,
    resolve_wechat_message_params,
)
