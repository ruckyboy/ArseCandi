import wx
import threading
import time


class TestFrame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, -1, "I am a test frame")
        self.clickbtn = wx.Button(self, label="click me!")
        self.Bind(wx.EVT_BUTTON, self.onClick)

    def onClick(self, event):
        self.clickbtn.Destroy()
        self.status = wx.TextCtrl(self)
        self.status.SetLabel("0")
        print("GUI will be responsive during simulated calculations...")
        thread = threading.Thread(target=self.runCalculation)
        thread.start()

    def runCalculation(self):
        print("you can type in the GUI box during calculations")
        retval = []
        for s in "1", "2", "3", "...":
            time.sleep(1)
            retval.append(s)
            wx.CallAfter(self.status.AppendText, s)
        wx.CallAfter(self.allDone, retval)

    def allDone(self, sometext):
        self.status.SetLabel("all done")
        dlg = wx.MessageDialog(self, f"This message shown only after calculation!\n{sometext}", "", wx.OK)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            self.Destroy()


mySandbox = wx.App()
myFrame = TestFrame()
myFrame.Show()
mySandbox.MainLoop()
