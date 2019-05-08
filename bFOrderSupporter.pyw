#bFOrderSupporter version 0.1 alpha
import tkinter
from tkinter import ttk,StringVar,DoubleVar,IntVar,BooleanVar,END,N,E,S,W
import pybitflyer
from tkinter.scrolledtext import ScrolledText

#Frameを継承
class OrderSupporter(tkinter.Frame):

    def __init__(self, master=None):
        super().__init__(master)
        #スクロールテキスト欄を宣言。width,heightをここで指定しないといけない？
        self.out = ScrolledText(self, width=40, height=12)

        self.clip_board = 0

        #api あえてファイルを2つに分けるのは良いと思う。セキュリティ的にも。実装も楽。envは面倒。
        self.api = pybitflyer.API(api_key=open('APIKey.txt').read(), api_secret=open('APISecret.txt').read())
        self.product_code = "FX_BTC_JPY"
        self.time_in_force = "GTC"

        #TKinterの変数
        self.amount = DoubleVar(value=0)
        self.entry_price_hundredth = IntVar(value=0) #entry_price_hundredthの下二桁は内部的にも省略。内部と外部を別に持つことによるバグを避けるため。使う時は×100する。
        self.broadcast_range = IntVar(value=100)
        self.broadcast_number = IntVar(value=10)
        self.cplimit_close_price = IntVar(value=0)
        self.trigger = IntVar(value=0)
        self.amount_proportion = DoubleVar(value=0.5)
        self.incdec_amount = DoubleVar(value=0.2)
        self.incdec_entry_price_hundredth = IntVar(value=10)
        self.check_price_or_not = BooleanVar(value=False)

        #描画関連
        self.interface()

#注文関連
    def current_price_stop_order(self):
        size = []
        price = []
        positions = self.api.getpositions(product_code=self.product_code)

        if not positions: #空リストだったら
            print("建玉はありません")
            self.out.insert(END, "建玉はありません\n"); self.out.see('end')
        elif 0 < float(self.amount_proportion.get()) <= 1: #ポジション割合が0～1か
            for pos in positions:
                size.append( pos['size'] )
                price.append( pos["price"] )
                side = pos["side"]
            # 平均建値と合計建玉を計算する
            average_price = round(sum( price[i] * size[i] for i in range(len(price)) ) / sum(size))
            sum_size = round(sum(size),2)
            print("保有中の建玉：合計{}つ\n 平均建値：{}円\n 合計建玉：{}枚\n 方向：{}".format(len(price),average_price,sum_size,side))
            self.out.insert(END, "保有中の建玉：合計{}つ\n 平均建値：{}円\n 合計建玉：{}枚\n 方向：{}\n".format(len(price),average_price,sum_size,side)); self.out.see('end')

            if side == "BUY":
                sside = "SELL"
                trigger_price = average_price - self.trigger.get()
            elif side == "SELL":
                sside = "BUY"
                trigger_price = average_price + self.trigger.get()

            if self.check_price(trigger_price, self.api.ticker(product_code=self.product_code)['ltp']):
                self.api.sendparentorder(
                    order_method = "SIMPLE",
                    # minute_to_expire = 100,
                    time_in_force =  self.time_in_force,
                    parameters = [
                        {
                            "product_code": self.product_code,
                            "condition_type": "STOP",
                            "side": sside,
                            "trigger_price": trigger_price,
                            "size": round(sum_size * float(self.amount_proportion.get()),2)
                        }
                    ]
                )
        else:
            print("CPSTOPの指定ロット割合には0より上、1以下を指定して下さい")
            self.out.insert(END, "CPSTOPの指定ロット割合には0より上、1以下を指定して下さい\n"); self.out.see('end')

    def current_price_limit_order(self):
        size = []
        price = []
        positions = self.api.getpositions(product_code=self.product_code)

        if not positions:
            print("建玉はありません")
            self.out.insert(END, "建玉はありません\n"); self.out.see('end')
        elif 0 < float(self.amount_proportion.get()) <= 1: #ポジション割合が0～1か
            for pos in positions:
                size.append( pos['size'] )
                price.append( pos["price"] )
                side = pos["side"]
            # 平均建値と合計建玉を計算する
            average_price = round(sum( price[i] * size[i] for i in range(len(price)) ) / sum(size))
            sum_size = round(sum(size),2)
            print("保有中の建玉：合計{}つ\n 平均建値：{}円\n 合計建玉：{}枚\n 方向：{}".format(len(price),average_price,sum_size,side))
            self.out.insert(END, "保有中の建玉：合計{}つ\n 平均建値：{}円\n 合計建玉：{}枚\n 方向：{}\n".format(len(price),average_price,sum_size,side)); self.out.see('end')

            if side == "BUY":
                    sside = "SELL"
                    trigger_price = average_price + self.cplimit_close_price.get()
            elif side == "SELL":
                    sside = "BUY"
                    trigger_price = average_price - self.cplimit_close_price.get()

            if self.check_price(trigger_price, self.api.ticker(product_code=self.product_code)['ltp']):
                self.api.sendchildorder(
                    # minute_to_expire=100,
                    time_in_force =  self.time_in_force,
                    product_code = self.product_code,
                    child_order_type = "LIMIT",
                    side = sside,
                    price = trigger_price,
                    size = round(sum_size * float(self.amount_proportion.get()),2)
                )
        else:
            print("CPLIMITの指定ロット割合には0より上、1以下を指定して下さい")
            self.out.insert(END, "CPLIMITの指定ロット割合には0より上、1以下を指定して下さい\n"); self.out.see('end')

    def limit_order_buy(self):
        self.limit_order(side="BUY")

    def limit_order_sell(self):
        self.limit_order(side="SELL")

    def limit_order(self, side):
        if self.check_price(self.entry_price_hundredth.get() * 100, self.api.ticker(product_code=self.product_code)['ltp']):
            self.api.sendchildorder(
                # minute_to_expire=100,
                time_in_force = self.time_in_force,
                product_code = self.product_code,
                child_order_type = "LIMIT",
                side = side,
                price = self.entry_price_hundredth.get() * 100,
                size = self.amount.get()
            )

    def market_order_buy(self):
        self.market_order(side="BUY")

    def market_order_sell(self):
        self.market_order(side="SELL")

    def market_order(self, side):
        self.api.sendchildorder(
            minute_to_expire = 100,
            time_in_force =  self.time_in_force,
            product_code = self.product_code,
            child_order_type = "MARKET",
            side = side,
            size = self.amount.get()
        )

    def stop_order_buy(self):
        self.stop_order(side="BUY")

    def stop_order_sell(self):
        self.stop_order(side="SELL")

    def stop_order(self, side):
        if side == "BUY":
            trigger_price = (int(self.entry_price_hundredth.get()) * 100) + self.trigger.get()
        elif side == "SELL":
            trigger_price = (int(self.entry_price_hundredth.get()) * 100) - self.trigger.get()

        if self.check_price(trigger_price, self.api.ticker(product_code=self.product_code)['ltp']):
            self.api.sendparentorder(
                order_method = "SIMPLE",
                # minute_to_expire = 100,
                time_in_force =  self.time_in_force,
                parameters = [
                    {
                        "product_code": self.product_code,
                        "condition_type": "STOP",
                        "side": side,
                        "trigger_price": trigger_price,
                        "size": self.amount.get()
                    }
                ]
            )

    def broadcast_order_sell(self):
        self.broadcast_order(side="SELL")

    def broadcast_order_buy(self):
        self.broadcast_order(side="BUY")

    def broadcast_order(self, side):
        #amountが空だとエラー出る。
        #api制限を考慮して一度に50以下に。
        if self.broadcast_number.get() > 50:
            print("バラマキ指値の数が多すぎます")
            self.out.insert(END, "バラマキ指値の数が多すぎます\n"); self.out.see('end')
        elif float(self.amount.get()) / float(self.broadcast_number.get()) < 0.01:
            print("ロットが少なすぎます")
            self.out.insert(END, "ロットが少なすぎます\n"); self.out.see('end')
        else:
            print("バラマキ" + side + "指値、開始")
            self.out.insert(END, "バラマキ" + side + "指値、開始\n"); self.out.see('end')

            #プラマイを掛けることで、BUYだと足して、SELLだと引いていく
            if side == "BUY":
                plus_or_minus = 1
            elif side == "SELL":
                plus_or_minus = -1
            #check_price用
            ltp = self.api.ticker(product_code=self.product_code)['ltp']

            #バラマキ数の数だけ繰り返す
            bn = self.broadcast_number.get()
            while bn > 0:
                    bn -= 1
                    price = (int(self.entry_price_hundredth.get()) * 100) + ((self.broadcast_range.get() * bn) * plus_or_minus)
                    size = round(float(self.amount.get()) / float(self.broadcast_number.get()),2)
                    print (" ロット:", size, "価格:", price)
                    self.out.insert(END, " ロット:{}, 価格:{}\n".format(size, price)); self.out.see('end')
                    #注文
                    if self.check_price(price, ltp):
                        self.api.sendchildorder(
                            # minute_to_expire=100,
                            time_in_force =  self.time_in_force,
                            product_code = self.product_code,
                            child_order_type = "LIMIT",
                            side = side,
                            price = price,
                            size = size
                        )

            print("バラマキ" + side + "指値、終了")
            self.out.insert(END, "バラマキ" + side + "指値、終了\n"); self.out.see('end')

    def cancel_all(self):
        self.api.cancelallchildorders(
            product_code=self.product_code
        )
        print("すべての注文をキャンセルします")
        self.out.insert(END, "すべての注文をキャンセルします\n"); self.out.see('end')


#注文関連以外
    def get_clipboard(self):
        #クリップボード監視
        #entry_price_hundredthなので、下二桁は取り除く。
        #クリップボードの中身が10進数以外の場合は弾く。
        #その上で、クリップボードの中身が前回と違う時のみ、set。
        #クリップボードが画像等の場合エラーで止まるので、無視してパス。
        try:
            clipboard_no_nakami = root.clipboard_get()
            if str.isdecimal(clipboard_no_nakami):
                if int(self.clip_board) != round(int(clipboard_no_nakami)/100):
                    self.clip_board = round(int(clipboard_no_nakami)/100)
                    self.entry_price_hundredth.set(self.clip_board)
                    print("クリップボード価格を取得しました:" + str(self.clip_board * 100))
                    self.out.insert(END, "クリップボード価格を取得しました:" + str(self.clip_board * 100) + "\n"); self.out.see('end')
        except:
            #print("clipboard_get error")
            pass

        #次のタイマーをセット。1秒に1回取得
        root.after(1000, self.get_clipboard)

    def clear_amount(self):
        self.amount.set(0)

    #増減
    def inc_amount(self):
        #一応増やす方も。ロットが0未満にならないように。if使いたくないがわからんので。
        if round(self.amount.get() + self.incdec_amount.get(), 2) >= 0:
            self.amount.set(round(self.amount.get() + self.incdec_amount.get(), 2))

    def dec_amount(self):
        if round(self.amount.get() - self.incdec_amount.get(), 2) >= 0:
            self.amount.set(round(self.amount.get() - self.incdec_amount.get(), 2))

    def inc_entry_price_hundredth(self):
        #entry_price_hundredthは下二桁省略。注意。
        self.entry_price_hundredth.set(self.entry_price_hundredth.get() + self.incdec_entry_price_hundredth.get())

        if self.clip_board != 0: #0初期化なので。
            print("クリップボード価格との差:" + str((self.entry_price_hundredth.get() - self.clip_board) * 100))
            self.out.insert(END, "クリップボード価格との差:" +  str((self.entry_price_hundredth.get() - self.clip_board) * 100) + "\n"); self.out.see('end')

    def dec_entry_price_hundredth(self):
        if (self.entry_price_hundredth.get() - self.incdec_entry_price_hundredth.get()) >= 0:
            self.entry_price_hundredth.set(self.entry_price_hundredth.get() - self.incdec_entry_price_hundredth.get())

        if self.clip_board != 0: #0初期化なので。
            #import pdb; pdb.set_trace()
            print("クリップボード価格との差:" + str((self.entry_price_hundredth.get() - self.clip_board) * 100))
            self.out.insert(END, "クリップボード価格との差:" +  str((self.entry_price_hundredth.get() - self.clip_board) * 100) + "\n"); self.out.see('end')

    def get_current_amount(self):
        #import pdb; pdb.set_trace()
        positions = self.api.getpositions(product_code=self.product_code)
        if positions == []:
            print("建玉はありません")
            self.out.insert(END, "建玉はありません\n"); self.out.see('end')
        else:
            #合計建玉を計算
            size = []
            for pos in positions:
                size.append( pos['size'] )
            sum_size = round(sum(size),2)
            self.amount.set(sum_size)

            print("合計建玉:"  + str(sum_size) + "枚")
            self.out.insert(END, "合計建玉:" + str(sum_size) + "枚\n"); self.out.see('end')

    def check_price(self, price, ltp): #このpriceは下二桁省略しない。
        #import pdb; pdb.set_trace()

        if self.check_price_or_not.get() == True:
            #ltp = self.api.ticker(product_code=self.product_code)['ltp']
            #print("LTPは" + str(ltp) + "です")
            #self.out.insert(END, "LTPは" + str(ltp) + "です\n"); self.out.see('end')
            if ltp * 1.05 > price > ltp * 0.95 :
                #print("注文価格が5%範囲内です")
                #self.out.insert(END, "注文価格が5%範囲内です\n"); self.out.see('end')
                return True
            else:
                print("注文価格が5%範囲外です")
                self.out.insert(END, "注文価格が5%範囲外です\n"); self.out.see('end')
                return False
        else:
            #print("5%範囲内価格チェックしません")
            #self.out.insert(END, "5%範囲内価格チェックしません\n"); self.out.see('end')
            return True

#描画関連
    def interface(self):
        #style = ttk.Style(root)
        root.title('bFOrderSupporter')

        #チェックボックス
        checkbox1 = tkinter.Checkbutton(self, text = "5％範囲内価格チェック(混雑時は遅くなるので注意)", variable = self.check_price_or_not)

        #ラベル
        #label14 = tkinter.Label(self, text='', height=0) #上の空白。あまり良くない。
        label1 = ttk.Label(self, text='ロット')
        label2 = ttk.Label(self, text='価格(下二桁省略)')
        label3 = ttk.Label(self, text='バラマキ指値の幅(マイナス可)')
        label4 = ttk.Label(self, text='バラマキ指値の数(1分に100回未満)')
        label5 = ttk.Label(self, text='CPLIMIT:利確幅')
        label7 = ttk.Label(self, text='逆指値, CPSTOP:損切り幅')
        label8 = ttk.Label(self, text='CPLIMIT,CPSTOP:建玉の割合(0～1)')
        label9 = ttk.Label(self, width=2, text='00')
        label10 = ttk.Label(self, text=' 指値', width=10)
        label11 = ttk.Label(self, text='バラマキ', width=10)
        label12 = ttk.Label(self, text='逆指値', width=10)
        label13 = ttk.Label(self, text='成り行き', width=10)

        #入力欄
        entry1 = ttk.Entry(self, width=6, textvariable=self.amount) #ロット
        entry2 = ttk.Entry(self, width=6, textvariable=self.entry_price_hundredth) #価格
        entry3 = ttk.Entry(self, width=6, textvariable=self.broadcast_range)
        entry4 = ttk.Entry(self, width=6, textvariable=self.broadcast_number)
        entry5 = ttk.Entry(self, width=6, textvariable=self.cplimit_close_price) #CPLIMIT:利確幅
        entry7 = ttk.Entry(self, width=6, textvariable=self.trigger) #逆指値, CPSTOP:損切り幅
        entry8 = ttk.Entry(self, width=6, textvariable=self.amount_proportion)
        entry9 = ttk.Entry(self, width=6, textvariable=self.incdec_amount)
        entry10 = ttk.Entry(self, width=6, textvariable=self.incdec_entry_price_hundredth)

        #ボタン ttkのbuttonの色は変えにくいので、tkinterのbuttonを使用
        button1 = tkinter.Button(self, text='買い指値',width=12, command=self.limit_order_buy, bg="green", fg="white")
        button2 = tkinter.Button(self, text='売り指値',width=12, command=self.limit_order_sell, bg="red", fg="white")
        button3 = tkinter.Button(self, text='バラマキ買い指値',width=12, command=self.broadcast_order_buy, bg="green", fg="white")
        button4 = tkinter.Button(self, text='バラマキ売り指値',width=12, command=self.broadcast_order_sell, bg="red", fg="white")
        button5 = tkinter.Button(self, text='CPLIMIT：合計建玉を利確幅指定して指値',width=40, command=self.current_price_limit_order)
        button6 = tkinter.Button(self, text='CPSTOP：合計建玉を損切り幅指定して逆指値',width=40, command=self.current_price_stop_order)
        button7 = tkinter.Button(self, text='売り逆指値',width=12, command=self.stop_order_sell, bg="red", fg="white")
        button8 = tkinter.Button(self, text='買い逆指値',width=12, command=self.stop_order_buy, bg="green", fg="white")
        button9 = tkinter.Button(self, text='全キャンセル',width=12, command=self.cancel_all)
        button10 = tkinter.Button(self, text='成り行き買い',width=12, command=self.market_order_buy, bg="green", fg="white")
        button11 = tkinter.Button(self, text='成り行き売り',width=12, command=self.market_order_sell, bg="red", fg="white")
        button16 = tkinter.Button(self, text='C',width=1, command=self.clear_amount)
        #button16 = tkinter.Button(self, text='C',width=1, command=self.check_price)
        button17 = tkinter.Button(self, text='合計建玉取得',width=10, command=self.get_current_amount)
        #ロット増減
        button12 = tkinter.Button(self, text='＋',width=2, command=self.inc_amount)
        button13 = tkinter.Button(self, text='ー',width=2, command=self.dec_amount)
        #価格増減
        button14 = tkinter.Button(self, text='＋',width=2, command=self.inc_entry_price_hundredth)
        button15 = tkinter.Button(self, text='ー',width=2, command=self.dec_entry_price_hundredth)


        ####位置
        #root.geometry("320x600")
        self.grid(row=0,column=0,sticky=(N,E,S,W))
        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=2)

        #チェックボックス
        checkbox1.grid(row=0, column=0, padx=0, ipadx=0, pady=0, ipady=0, columnspan=7)

        #ラベル
        #label14.grid(row=0, column=1, padx=0, ipadx=0, pady=0, ipady=0)
        label1.grid(row=1, column=0, sticky=E, columnspan=2, pady=0, ipadx=0, ipady=0)
        label2.grid(row=2, column=0, sticky=E, columnspan=2)
        label3.grid(row=3, column=0, sticky=E, columnspan=2)
        label4.grid(row=4, column=0, sticky=E, columnspan=2)
        label5.grid(row=5, column=0, sticky=E, columnspan=2)
        label7.grid(row=7, column=0, sticky=E, columnspan=2)
        label8.grid(row=8, column=0, sticky=E, columnspan=2)
        label9.grid(row=2, column=3, sticky=W, padx=0, ipadx=0)
        label10.grid(row=10, column=1, columnspan=2, sticky=W)
        label11.grid(row=11, column=1, columnspan=2, sticky=W)
        label12.grid(row=14, column=1, columnspan=2, sticky=W)
        label13.grid(row=16, column=1, columnspan=2, sticky=W)

        #入力欄
        entry1.grid(row=1, column=2, sticky=S+W, padx=0, ipadx=0)
        entry2.grid(row=2, column=2, sticky=W, padx=0, ipadx=0)
        entry3.grid(row=3, column=2, sticky=W, padx=0, ipadx=0)
        entry4.grid(row=4, column=2, sticky=W, padx=0, ipadx=0)
        entry5.grid(row=5, column=2, sticky=W, padx=0, ipadx=0)
        entry7.grid(row=7, column=2, sticky=W, padx=0, ipadx=0)
        entry8.grid(row=8, column=2, sticky=W, padx=0, ipadx=0)
        entry9.grid(row=1, column=0, sticky=S+W)
        entry10.grid(row=2, column=0, sticky=W)

        #ボタン
        button1.grid(row=10, column=2, sticky=E, columnspan=4)
        button2.grid(row=10, column=0, sticky=W)
        button3.grid(row=11, column=2, sticky=E, columnspan=4)
        button4.grid(row=11, column=0, sticky=W)
        button5.grid(row=12, column=0, columnspan=6)
        button6.grid(row=13, column=0, columnspan=6)
        button7.grid(row=14, column=2, sticky=E, columnspan=4)
        button8.grid(row=14, column=0, sticky=W)
        button9.grid(row=15, column=0, columnspan=6)
        button10.grid(row=16, column=2, sticky=E, columnspan=4)
        button11.grid(row=16, column=0, sticky=W)
        button12.grid(row=1, column=4, sticky=S+E, ipadx=0, ipady=0)
        button13.grid(row=1, column=5, sticky=S+E)
        button14.grid(row=2, column=4, sticky=E)
        button15.grid(row=2, column=5, sticky=E)
        button16.grid(row=1, column=3, sticky=W+E+S, padx=0, ipadx=0)
        button17.grid(row=3, column=3, padx=0, ipadx=0, columnspan=3, pady=0, ipady=0)

        #スクロールテキスト
        self.out.grid(row=17, column=0, sticky=W,  columnspan=7)


if __name__ == '__main__':
    root = tkinter.Tk()

    order = OrderSupporter(master=root)
    order.after(1000, order.get_clipboard) #クリップボード監視
    order.mainloop()

