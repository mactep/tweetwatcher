# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# This is the backend for the UI as defined in grudi.py

# This uses PTT. Check: https://github.com/sixohsix/twitter
# This is an alternative to track_to_database.py, which uses
# a different API.
# If using this with version twitter-1.18.0, don't forget to
# add into twitter/cmdline.py the following line after line 526:
#
#                tweet_mode="extended",
#
# as instructed in https://github.com/sixohsix/twitter/issues/398

from grudi import Ui_MainWindow
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtCore, QtGui, QtWidgets
from twitter import *
from time import sleep, time
from threading import Thread

import sqlite3
import os
import json
import sys

from os.path import isfile

def get_credentials():
    if isfile('credentials'):
        with open('credentials', 'r') as f:
            return [line.strip() for line in f.readlines()]
    else:
        return ['', '', '', '', '']

class TextOutputWithSignal(QObject):
    received_text = pyqtSignal(str, name='receivedText')
    def __init__(self, textEditOutput):
        super().__init__()
        self.textEditOutput = textEditOutput

class Backend(Ui_MainWindow):
    def __init__(self):
        super().__init__()
    
    def init_stuff(self): # run after ui.setupUi()..
        self.searching = False
        self.stop_searching = False
        self.counter = 0
        self.textEditOutput = TextOutputWithSignal(self.textEditOutput)
        self.searchPushButtonSearch.clicked.connect(self.start_thread)
        self.cancelPushButtonSearch.clicked.connect(self.set_stop)
        self.textEditOutput.received_text.connect(self.append_text)
        self.pushButtonDatabasePathSearch.clicked.connect(self.select_file)

        token, token_secret, consumer_key, consumer_secret, database_path = get_credentials()
        self.lineAccessToken.setText(token)
        self.lineAccessTokenSecret.setText(token_secret)
        self.lineConsumerKey.setText(consumer_key)
        self.lineConsumerSecret.setText(consumer_secret)
        self.lineDatabasePathSearch.setText(database_path)
        
        '''
        gray_style_sheet = QLineEdit[readOnly=\"True\"] {
              color: #808080;
              background-color: #F0F0F0;"
              border: 1px solid #B0B0B0;"
              border-radius: 2px;}
        self.lineAccessToken.setStyleSheet(gray_style_sheet)
        self.lineAccessTokenSecret.setStyleSheet(gray_style_sheet)
        self.lineConsumerKey.setStyleSheet(gray_style_sheet)
        self.lineConsumerSecret.setStyleSheet(gray_style_sheet)
        self.lineDatabasePathSearch.setStyleSheet(gray_style_sheet)
        self.lineSearchTerms.setStyleSheet(gray_style_sheet)
        '''
    
    def select_file(self):
        self.lineDatabasePathSearch.setText(QFileDialog.getOpenFileName()[0])

    def append_text(self, text):
        print("Received signal. Appending.")
        self.textEditOutput.textEditOutput.append(text)
        print("Appended. Now moving cursor to the end.")
        self.textEditOutput.textEditOutput.moveCursor(QtGui.QTextCursor.End)
        print("Moved cursor.")
        self.lineEditFound.setText(str(self.counter))

    def set_stop(self):
        self.stop_searching = True
    
    def search(self):
        self.searchPushButtonSearch.setText('Searching...')
        
        self.lineAccessToken.setReadOnly(True)
        self.lineAccessTokenSecret.setReadOnly(True)
        self.lineConsumerKey.setReadOnly(True)
        self.lineConsumerSecret.setReadOnly(True)
        self.lineDatabasePathSearch.setReadOnly(True)
        self.lineSearchTerms.setReadOnly(True)

        now = time()
        #token = '890399609071312896-LV9nqPsPaj0nDUiZxJLxAQndVlNyzRq'
        #token_secret = 'A8x38tR8K1otXMH1vWSTb5jgkEonvVeSbrCRj7AiOQz7h'
        #consumer_key = 'JNDKMfAylkZqwFsRbR0RVf2hO'
        #consumer_secret = 'vfG7AorVSUor0VJFj7wmxjNHtOHpL3kWTJHkaNREnorzq5qJYc'
        #terms = self.track.split(',')
        #conn = sqlite3.connect('C:\\Users\\fuck you\\Desktop\\db.db')
        
        token = self.lineAccessToken.text()
        token_secret = self.lineAccessTokenSecret.text()
        consumer_key = self.lineConsumerKey.text()
        consumer_secret = self.lineConsumerSecret.text()
        terms = self.lineSearchTerms.text()#.split(',')
        conn = sqlite3.connect(self.lineDatabasePathSearch.text())
        
        cur = conn.cursor()

        for t in terms:
            cur.execute('CREATE TABLE IF NOT EXISTS ' + '`[{}]`'.format(t) + ' (\nid integer PRIMARY KEY,\ntimestamp INTEGER,\nresponse TEXT\n);')

        print('Initiating stream...')
        
        twitter_stream = TwitterStream(
            auth=OAuth(token, token_secret, consumer_key, consumer_secret))

        iterator = twitter_stream.statuses.filter(track=terms, stall_warnings=True)

        print('Searching for {}'.format(terms))

        for tweet in iterator:
            keys = tweet.keys()
            
            if 'retweeted_status' in keys:
                try:
                    text = tweet['retweeted_status']['extended_tweet']['full_text']
                except KeyError:
                    text = tweet['retweeted_status']['text']
            else:
                try:
                    text = tweet['extended_tweet']['full_text']
                except KeyError:
                    try:
                        text = tweet['text']
                    except KeyError:
                        continue
            
            for t in terms:
                if t.lower() in text.lower():
                    cur.execute('INSERT INTO ' + '`[{}]`'.format(t) + '(timestamp,response)\nVALUES(?,?)', (int(time()), json.dumps(tweet)))
                    self.counter += 1
                    if not (self.counter % 50):
                        conn.commit()
                        print('Committed at ' + str(int(time())))

            if time() - now > 5:
                print('Sending signal.')
                self.textEditOutput.received_text.emit(text)
                print('Sent signal.')
                now = time()
                        
            if self.stop_searching:
                self.stop_searching = False
                self.searching = False
                self.lineAccessToken.setReadOnly(False)
                self.lineAccessTokenSecret.setReadOnly(False)
                self.lineConsumerKey.setReadOnly(False)
                self.lineConsumerSecret.setReadOnly(False)
                self.lineDatabasePathSearch.setReadOnly(False)
                self.lineSearchTerms.setReadOnly(False)

                self.searchPushButtonSearch.setText('Search')
                print('Stopped searching.')
                break
    
    def start_thread(self):
        if not self.searching:
            print('Starting thread.')
            Thread(target = self.search).start()
            self.searching = True
            print('Returning from start_thread().')

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Backend()
    ui.setupUi(MainWindow)
    ui.init_stuff()
    MainWindow.show()
    sys.exit(app.exec_())