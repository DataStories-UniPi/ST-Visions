"""
    filter_callbacks.py - v2025.05.18

    Authors: Paraschos Moraitis, Andreas Tritsarolis
"""

import abc
import bokeh.models as bokeh_mdl

class ST_BokehFilters:
    __metaclass__ = abc.ABCMeta
    """
    Abstract base class for interactive filter widgets in VISIONS instances
    """

    def __init__(self, vsn_instance, widget):
        """
        Initialize BokehFilters instance.

        """
        self.widget = widget
        self.vsn_instance = vsn_instance

    def _suppress_callbacks(self, widget):
        """
        Context manager to temporarily suppress callbacks on a widget.
        """
        from contextlib import contextmanager
        
        @contextmanager
        def suppress_bokeh_callbacks(w):
            old_callbacks = w._callbacks.copy()
            w._callbacks.clear()
            try:
                yield
            finally:
                w._callbacks.update(old_callbacks)
        
        return suppress_bokeh_callbacks(widget)

    def callback_filter_data(self):
        """
        Coordinate filter execution across all connected widgets.
        
        Notes
        -----
        This method should be called **first** in any custom callback implementation.
        It suppresses callbacks on other widgets while collecting their current states.
        """
        # Trigger updates on all other widgets with callbacks suppressed
        for other_widget in self.vsn_instance.widgets:
            if other_widget.id == self.widget.id:
                continue  # Skip the current widget
            
            # Get the callback policy for this widget
            callback_keys = list(other_widget._callbacks.keys())
            if not callback_keys:
                continue
            
            widget_callback_policy = callback_keys[0]
            
            # Suppress callbacks while triggering update
            with self._suppress_callbacks(other_widget):
                other_widget.trigger(widget_callback_policy, None, other_widget.value)

    def get_data(self):
        """
        Retrieve the appropriate dataset for filtering operations.
        
        Returns
        -------
        pandas.DataFrame or geopandas.GeoDataFrame
            The original dataset (always start from full data).
        
        Notes
        -----
        Always returns the full dataset to ensure ALL filters are reapplied
        from scratch during each update.
        """
        return self.vsn_instance.data

    def callback_prepare_data(self, new_pts):
        """
        Prepare filtered data for visualization rendering.
        
        Notes
        -----
        This method should be called **last** in any custom callback implementation.
        """
        prepared_data = self.vsn_instance.prepare_data(new_pts)

        # Update color mapper factors for categorical coloring
        if (self.vsn_instance.cmap is not None and 
            isinstance(self.vsn_instance.cmap['transform'], bokeh_mdl.CategoricalColorMapper)):
            
            factors = sorted(
                prepared_data[
                    self.vsn_instance.cmap['field']
                ].unique().tolist()
            )
            self.vsn_instance.cmap['transform'].factors = factors

        self.vsn_instance.source.data = prepared_data.drop(prepared_data.geometry.name, axis=1).to_dict(orient="list")

    @abc.abstractmethod
    def callback(self, *args):
        pass