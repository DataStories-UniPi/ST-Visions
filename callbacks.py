'''
	callbacks.py - v2020.05.12

	Authors: Andreas Tritsarolis, Christos Doulkeridis, Yannis Theodoridis and Nikos Pelekis
'''    


import abc
import bokeh.models as bokeh_mdl


class BokehFilters:
    __metaclass__ = abc.ABCMeta

    def __init__(self, vsn_instance, widget):
        '''
        Constructor for the BokehFilters Class.
          * vsn_instance: The VISIONS instance that the BokehFilters instance will be connected to
          * widget: The widget that the callback will be intended for    
        '''
        self.widget = widget
        self.vsn_instance = vsn_instance


    def callback_filter_data(self):
        '''
        Iteratively triggers the widgets' callback methods in order to filter the data. 
        This method is reccommended to be placed first in a custom callback method
        '''
        if not self.vsn_instance.aquire_canvas_data:
            self.vsn_instance.aquire_canvas_data = self.widget.id
            
            for widget in self.vsn_instance.widgets:
                if not widget.id == self.widget.id:
                    widget_callback_policy = list(widget._callbacks.keys())[0] 
                    widget.trigger(widget_callback_policy, None, widget.value)


    def get_data(self):
        '''
        Fetches the data. If the lock is aquired:
          * If the intermediate storage (canvas_data) is empty fetch the loaded dataset; otherwise
          * Fetch the filtered data via the intermediate storage.
        '''
        if self.vsn_instance.aquire_canvas_data and (self.vsn_instance.canvas_data is not None):        
            # print ('Fetching Filtered Data')
            return self.vsn_instance.canvas_data
        else:
            # print ('Fetching OG Data')
            return self.vsn_instance.data


    def callback_prepare_data(self, new_pts, ready_for_output):
        '''
        Preparing the Filtered data prior to rendering (i.e., passing them to the CDS). 
        This method is recommended to be placed last in a custom callback method
        '''
        self.vsn_instance.canvas_data = new_pts

        if ready_for_output:
            self.vsn_instance.canvas_data = self.vsn_instance.prepare_data(self.vsn_instance.canvas_data)

            if (self.vsn_instance.cmap is not None) and (isinstance(self.vsn_instance.cmap['transform'], bokeh_mdl.CategoricalColorMapper)):
                factors = sorted(self.vsn_instance.canvas_data[self.vsn_instance.cmap['field']].unique().tolist())
                self.vsn_instance.cmap['transform'].factors = factors

            self.vsn_instance.source.data = self.vsn_instance.canvas_data.drop(self.vsn_instance.canvas_data.geometry.name, axis=1).to_dict(orient="list")

            # print ('Releasing Lock...')
            self.vsn_instance.canvas_data = None
            self.vsn_instance.aquire_canvas_data = None


    @abc.abstractmethod
    def callback(self, attr, old, new):
        pass