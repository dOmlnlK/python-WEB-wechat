from django.shortcuts import render,HttpResponse
import requests
import time
import re
import json
from bs4 import BeautifulSoup
# Create your views here.


ctime = None
qcode = None
tip = 1
ticket_dic = {}
init_dic = {}
all_cookies = {}
def wechat_login(request):
    global ctime
    ctime = time.time()
    response = requests.get("https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&fun=new&lang=zh_CN&_=%s"%ctime)
    global qcode
    qcode = re.findall(r'uuid = "(.*==)"',response.text)[0]

    return render(request,"login.html",{"qcode":qcode})


def check_login(request):
    callback = {"status":None,"avator_src":None}
    ret = requests.get("https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=%s&tip=%s&r=326157957&_=%s"%(qcode,tip,ctime))
    global tip
    tip =1

    if "window.code=201" in ret.text:
        """已扫码未确认登录"""
        avator_src = re.findall(r"userAvatar = '(.*)'" ,ret.text)[0]
        callback["status"]=201
        callback["avator_src"]=avator_src
        global tip
        tip = 0
    elif "window.code=408" in ret.text:
        """无人扫码"""
        callback["status"]=408

    elif "window.code=200" in ret.text:
        #获取凭证
        callback["status"]=200
        redirect_uri = re.findall(r'redirect_uri="(.*)"',ret.text)[0] + "&fun=new&version=v2&lang=zh_CN"
        r1 = requests.get(redirect_uri)
        all_cookies.update(r1.cookies.get_dict())
        soup = BeautifulSoup(r1.text,"html.parser")

        for tag in soup.find("error").children:
            ticket_dic[tag.name] = tag.get_text()

    return HttpResponse(json.dumps(callback))


def wechat_user(request):
    get_user_info_data = {
        "BaseRequest": {
            "DeviceID": "e285116988555068",
            "Sid": ticket_dic["wxsid"],
            "Skey": ticket_dic["skey"],
            "Uin": ticket_dic["wxuin"]
        }
    }
    get_user_info = requests.post(
        "https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=311068530&lang=zh_CN&pass_ticket=" + ticket_dic['pass_ticket'],
        json=get_user_info_data
    )
    get_user_info.encoding = "utf-8"
    user_init_dic = json.loads(get_user_info.text)
    init_dic.update(user_init_dic)
    ContactList = user_init_dic["ContactList"] #最近联系人
    MPSubscribeMsgList = user_init_dic["MPSubscribeMsgList"]  #公众号

    return render(request,"user.html",{"ContactList":ContactList,"MPSubscribeMsgList":MPSubscribeMsgList})


def contact_list(request):
    ctime = time.time()
    base_url = "https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket=%s&r=%s&seq=0&skey=%s"
    get_contact_url = base_url %(ticket_dic["pass_ticket"],ctime,ticket_dic["skey"])

    contact_data = requests.get(get_contact_url,cookies=all_cookies)
    contact_data.encoding = "utf-8"
    contact_dic = json.loads(contact_data.text)


    return render(request,"contact_list.html",{"contact_dic":contact_dic})



def send_msg(request):

    toUser = request.GET.get("toUser")
    msg = request.GET.get("msg")
    send_url = "https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=%s"%ticket_dic["pass_ticket"]
    post_dic = {
        "BaseRequest": {
            "DeviceID": "e285116988555068",
            "Sid": ticket_dic["wxsid"],
            "Skey": ticket_dic["skey"],
            "Uin": ticket_dic["wxuin"]
        },
        "Msg":{
            "ClientMsgId": str(int(time.time()*1000)),
            "Content": msg,
            "FromUserName": init_dic["User"]["UserName"],
            "LocalID": str(int(time.time()*1000)),
            "ToUserName": toUser,
            "Type": 1
        }
    }
    print(post_dic)

    response = requests.post(send_url,data=bytes(json.dumps(post_dic,ensure_ascii=False),encoding="utf-8"))
    print(">>",response.text)
    return HttpResponse("ok")