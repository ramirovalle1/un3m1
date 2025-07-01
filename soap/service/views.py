#!/usr/bin/env python
from spyne.service import ServiceBase
from spyne.decorator import srpc
from spyne.model.primitive import DateTime, Unicode, AnyDict


class AvayaService(ServiceBase):
    @srpc(DateTime, DateTime, Unicode, Unicode, Unicode, Unicode, Unicode, Unicode, Unicode, Unicode, _returns=(AnyDict))
    def call_data(start_date, end_date, duration, call_type, extension, DNIS, CLID, agent, rec_number, UCID):
        dictionary = {
            'start_date': start_date,
            'end_date': end_date,
            'extension': extension,
            'call_type': call_type,
            'DNIS': DNIS,
            'CLID': CLID,
            'agent': agent,
            'rec_number': rec_number,
            'UCID': UCID
        }
        print(dictionary)
        return dictionary
