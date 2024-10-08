# Copyright (c) 2024, Tri Dao, Albert Gu.
# Copyright (c) 2024, NVIDIA CORPORATION. All rights reserved.

# Some of this code was adopted from https://github.com/state-spaces/mamba/
# This source code is licensed under the Apache license found in the
# LICENSE file in the root directory of this source tree.

import math
import torch
from functools import partial
from typing import Optional, Union

from dataclasses import dataclass

from torch import nn, Tensor
from megatron.core.transformer.module import MegatronModule
from mamba_ssm import Mamba
from megatron.core.transformer.spec_utils import ModuleSpec, build_module
from megatron.core.transformer.identity_op import IdentityFuncOp, IdentityOp

from megatron.core.transformer.transformer_config import TransformerConfig


# from megatron.core.transformer.spec_utils import ModuleSpec
# from megatron.core.transformer.transformer_layer import TransformerLayer, TransformerLayerSubmodules

@dataclass
class MambaLayerSubmodules:
    norm: Union[ModuleSpec, type] = IdentityOp
    mixer: Union[ModuleSpec, type] = IdentityOp

class MambaLayer(MegatronModule):
    def __init__(
        self,
        config: TransformerConfig,
        submodules: MambaLayerSubmodules,
        layer_idx=None,
        residual_in_fp32=False,
        **kwargs,
    ):
        """
        Top level Mamba Layer
        """
        super().__init__(config)
        self.config = config
        self.residual_in_fp32 = residual_in_fp32
        self.mixer = build_module(
            submodules.mixer,
            self.config,
            self.config.hidden_size,
            layer_idx=layer_idx,
            **kwargs
        )
        self.norm = build_module(submodules.norm,
                                 self.config,
                                 self.config.hidden_size
        )

    def forward(
        self,
        hidden_states: Tensor,
        attention_mask: Tensor, # Not used in MambaLayer
        inference_params=None,
        rotary_pos_emb: Tensor=None, # Not used in MambaLayer
        **kwargs
    ):

        residual = hidden_states
        hidden_states = self.norm(residual.to(dtype=self.norm.weight.dtype))
        if self.residual_in_fp32:
            residual = residual.to(torch.float32)

        hidden_states = self.mixer(hidden_states, inference_params=inference_params)
        return hidden_states+residual

    def allocate_inference_cache(self, batch_size, max_seqlen, dtype=None, **kwargs):
        return self.mixer.allocate_inference_cache(batch_size, max_seqlen, dtype=dtype, **kwargs)
