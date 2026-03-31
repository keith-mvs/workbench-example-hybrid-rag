# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from docs import DocProcessor

# Check environment variables for docmark preprocessing
ENABLE_DOCMARK = os.getenv('DOCMARK_PREPROCESS', 'false').lower() == 'true'
DOCMARK_LEVEL = os.getenv('DOCMARK_CLEANING_LEVEL', 'medium')

p = DocProcessor(
    "/project/data/documents", 
    "/mnt/docs", 
    "http://localhost:8000/uploadDocument", 
    log=False,
    preprocess_with_docmark=ENABLE_DOCMARK,
    docmark_cleaning_level=DOCMARK_LEVEL
)
p.process()
exit(0)