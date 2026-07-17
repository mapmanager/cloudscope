# Python client

```python
from __future__ import annotations

import numpy as np
import requests

base_url = 'http://127.0.0.1:8000'
opened_response = requests.post(
    f'{base_url}/api/v2/open',
    json={
        'path': '/absolute/path/to/acquisition.oir',
        'channelIndices': [0, 1],
    },
    timeout=180,
)
opened_response.raise_for_status()
opened = opened_response.json()

channel = opened['channels'][0]
binary_response = requests.get(
    f"{base_url}{channel['dataUrl']}",
    timeout=180,
)
binary_response.raise_for_status()

shape = tuple(opened['plane']['shape'])
array = np.frombuffer(binary_response.content, dtype='<f4').reshape(shape)
```

The returned NumPy array follows the reported `plane.shape`. The server does not
transpose it for plotting libraries.
