#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .order_type import *
from .order_status import *
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class OrderManager(object):
    '''
    Manage/track all the orders
    '''
    def __init__(self):
        self.order_dict = {}              # order_id ==> order
        self.fill_dict = {}                # fill_id ==> fill
        self.standing_order_set = set()        # order_id of standing order for convenience
        self.canceled_order_set = set()  # order_id of canceled orders for convenience

    def reset(self):
        self.order_dict.clear()
        self.fill_dict.clear()
        self.standing_order_set.clear()
        self.canceled_order_set.clear()

    def on_tick(self, tick_event):
        """
        """
        pass

    def on_order_status(self, order_event):
        """
        on order status change from broker
        including canceled status
        """
        # there should be no negative order id if order is directly placed without queue.
        if order_event.order_id < 0:
            _logger.error(f'received negative orderid {order_event.order_id}')

        if order_event.order_id in self.order_dict:
            if (order_event.full_symbol != self.order_dict[order_event.order_id].full_symbol):
                _logger.error("Error: orders dont match")
                return False
            # only change status when it is logical
            elif self.order_dict[order_event.order_id].order_status.value <= order_event.order_status.value:
                self.order_dict[order_event.order_id].order_status = order_event.order_status
                if order_event.order_status < OrderStatus.FILLED:
                    self.standing_order_set.add(order_event.order_id)
                return True
            else:  # no need to change status
                return False
        # order_id not yet assigned, open order at connection or placed by trader?
        else:
            self.order_dict[order_event.order_id] = order_event
            if order_event.order_status < OrderStatus.FILLED:
                self.standing_order_set.add(order_event.order_id)
            return True

    def on_cancel(self, o):
        """
        TODO: remove on cancel? It's one order status
        :param o:
        :return:
        """
        self.canceled_order_set.add(o.order_id)
        if o.order_id in self.order_dict.keys():
            self.order_dict[o.order_id].order_status = OrderStatus.CANCELED
            if o.order_id in self.standing_order_set:
                self.standing_order_set.remove(o.order_id)
        else:
            _logger.error('cancel order is not registered')

    def on_fill(self, fill_event):
        """
        on receive fill_event from broker
        """
        if fill_event.fill_id in self.fill_dict.keys():
            _logger.error('fill exists')
        else:
            self.fill_dict[fill_event.fill_id] = fill_event

            if fill_event.order_id in self.order_dict:
                self.order_dict[fill_event.order_id].fill_price = (fill_event.fill_price * fill_event.fill_size \
                                                                  + self.order_dict[fill_event.order_id].fill_price * self.order_dict[fill_event.order_id].fill_size) / \
                                                                  (self.order_dict[fill_event.order_id].fill_size + fill_event.fill_size)
                self.order_dict[fill_event.order_id].fill_size += fill_event.fill_size

                if self.order_dict[fill_event.order_id].order_size == self.order_dict[fill_event.order_id].fill_size:
                    self.order_dict[fill_event.order_id].order_status = OrderStatus.FILLED
                    if fill_event.order_id in self.standing_order_set:
                        self.standing_order_set.remove(fill_event.order_id)
                else:
                    self.order_dict[fill_event.order_id].order_status = OrderStatus.PARTIALLY_FILLED
            else:
                _logger.error(f'Fill event {fill_event.fill_id} has no matching order {fill_event.order_id}')

    def retrieve_order(self, order_id):
        try:
            return self.order_dict[order_id]
        except:
            return None

    def retrieve_fill(self, fill_id):
        try:
            return self.fill_dict[fill_id]
        except:
            return None

    def retrieve_standing_orders(self):
        oids = []
        for oid in self.standing_order_set:
            if oid in self.order_dict.keys():
                if self.order_dict[oid].order_status < OrderStatus.FILLED:  # has standing order
                    oids.append(oid)
        return oids
