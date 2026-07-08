"""Exercise the AcqTrace ABF API and plot all sweeps with Plotly.

Edit the hard-coded ``path`` value below, then run from the repository root:

    uv run python scripts/acqstore/try_abfile.py
"""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from acqstore.acq_trace.acq_trace import AcqTrace


def main() -> None:
    """Load one ABF file, print an overview, and plot every sweep.

    Returns:
        None.
    """
    path = '/Users/cudmore/data/theanne-griffith/07.20.21/2021_07_20_0016.abf'
    path = '/Users/cudmore/data/theanne-griffith/07.21.21/2021_07_21_0024.abf'

    channel_index = 0

    trace = AcqTrace(path)
    print(trace.info())
    print()
    print('summary:')
    print(trace.to_summary_dict())
    print()
    print('epoch table head:')
    print(trace.get_epoch_table(channel_index=channel_index).head())

    header = trace.trace_header
    num_sweeps = header.num_sweeps
    print(f'num_sweeps={num_sweeps}')

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            f'Channel {channel_index} ({header.channel_units[channel_index]})',
            f'DAC Command ({header.command_units[0] if header.command_units else ""})',
            'Epoch Labels',
        ),
    )
    for sweep_index in range(num_sweeps):
        sweep_table = trace.get_sweep_trace_table(
            channel_index=channel_index,
            sweep_index=sweep_index,
        )

        fig.add_trace(
            go.Scatter(
                x=sweep_table['time_sec'],
                y=sweep_table['value'],
                mode='lines',
                name=f'sweep {sweep_index}',
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=sweep_table['time_sec'],
                y=sweep_table['command'],
                mode='lines',
                name=f'command {sweep_index}',
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=sweep_table['time_sec'],
                y=sweep_table['epoch'],
                mode='lines',
                name=f'epoch {sweep_index}',
            ),
            row=3,
            col=1,
        )

    fig.update_xaxes(title_text='Time (s)', row=3, col=1)
    fig.update_yaxes(title_text=header.channel_units[channel_index], row=1, col=1)
    if header.command_units:
        fig.update_yaxes(title_text=header.command_units[0], row=2, col=1)
    fig.update_yaxes(title_text='Epoch', row=3, col=1)
    fig.update_layout(
        title=f'{trace.name} channel={channel_index} ({num_sweeps} sweeps)',
        height=900,
        showlegend=True,
    )
    fig.show()


if __name__ == '__main__':
    main()
