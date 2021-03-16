#!/usr/bin/python3
# coding: utf-8

__author__ = '@zNairy'
__contact__ = 'Github: https://github.com/znairy || Discord: __Nairy__#7181'
__version__ = '2.0'

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from termcolor import colored
from pathlib import Path
from random import sample
from os import uname, system
from shutil import rmtree
from json import loads, dumps
from threading import Thread

class Server(object):
    def __init__(self, host='0.0.0.0', port=5000, reqconn=5):
        self.address = (host, port)
        self.requestConnection = reqconn
        self.connectedUsers = {}
        self.__server = None
    
    def configureSocketConnection(self):
        server = socket(AF_INET, SOCK_STREAM)
        server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server.setblocking(1)
        server.bind(self.address)
        server.listen(self.requestConnection)
        return server

    def listenConnections(self):
        try:
            while True:
                connection, address = self.__server.accept()
                self.startProcess(self.verifyUserProfile, (connection, address))
        except KeyboardInterrupt:
            self.removeWaitRoomFolder()
    
    def startProcess(self, function, args):
        thread = Thread(target=function, args=args)
        thread.daemon = True
        thread.start()

    def showServerInfo(self):
        self.clearScreen()
        print(colored(f'        Servidor online em {self.address[0]}:{self.address[1]}  |   Usuários ativos: {self.totalUsersOnline()}    ', 'yellow'))

    def clearScreen(self):
        system('clear' if uname().sysname.lower() == 'linux' else 'cls')

    def allCommands(self):
        commands = {
            "/version": {"description": __version__, "function": self.sendVersion},
            "/contact": {"description": __contact__, "function": self.sendContact},
            "/author": {"description": __author__, "function": self.sendCodeAuthor},
            "/private": {"description": "Envie convite para uma sala privada com alguém. Ex: /private zNairy", "function": self.createPrivateInvite},
            "/unvite": {"description": "Remove um pedido para sala privada com alguém. Ex: /unvite zNairy", "function": self.cancelPrivateInvite},
            "/accept": {"description": "Aceita o convite de um usuário para um sala privada. Ex: /accept zNairy", "function": self.acceptPrivateInvite},
            "/decline": {"description": "Recusa um convite para sala privada feito por algum usuário. Ex: /decline zNairy", "function": self.declinePrivateInvite},
            "/leave": {"description": "Deixa uma sala privada com algum usuário.", "function": self.leaveFromPrivate},
            "/invites": {"description": "", "function": self.receivedInvites},
            "/namecolor": {},
            "/clear": {},
            "/exit": {}
        }

        commands.update({"/commands": {"description": '\n'+''.join(f'    {command}\n' for command in commands.keys()), "function": self.sendAvailableCommands}})

        return commands
    
    def checkCommand(self, user, data):
        command, args = self.splitReceivedCommand(data['message'].split())

        if command:
            params = {"description": command['description'], "userData": data, "functionArgs": args} 
            command['function'](user, params)
        else:
            self.sendMessageTo(user, 'Comando inválido ou inexistente...')
    
    def splitReceivedCommand(self, command):
        if self.allCommands().get(command[0]):
            return self.allCommands()[command[0]], command[1:]

        return False, command[1:]

    def sendAvailableCommands(self, user, params):
        self.sendMessageTo(user, params['description'])

    def codenameExists(self, codename):
        if Path(f'.server/registeredUsers/{codename}.json').is_file():
            return True
    
    def validIdentifier(self, profile):
        if self.codenameExists(profile['codename']):
            if profile['identifier'] == self.openUserProfile(profile['codename'])['identifier']:
                return True
    
    def createNewIdentifier(self):
        return ''.join(str(num) for num in sample(range(0, 10), 9))
    
    def createRegistredUsersFolder(self):
        if not Path('.server/registeredUsers').is_dir(): Path('.server/registeredUsers').mkdir(parents=True)
    
    def createUserData(self, codename, connection):
        return {codename: {"connectionAddress": connection, "onPrivate": {} }}
    
    def loginUser(self, connection, codename):
        self.connectedUsers.update(self.createUserData(codename, connection))
        self.startProcess(self.listenUserMessages, (connection, codename))
        self.showServerInfo()

    def openUserProfile(self, codename):
        with open(f'.server/registeredUsers/{codename}.json', 'rb') as userProfile:
            return loads(userProfile.read())
    
    def receiveProfileData(self, connection):
        return connection.recv(128)
    
    def saveUserProfile(self, profile):
        with open(f'.server/registeredUsers/{profile["codename"]}.json', 'w') as userProfile:
            userProfile.write(dumps({"identifier": profile['identifier']}))
    
    def totalUsersOnline(self):
        return len(self.connectedUsers)
    
    def userOnline(self, codename):
        if self.connectedUsers.get(codename):
            return True
    
    def verifyUserProfile(self, connection, address):
        profile = self.receiveProfileData(connection)

        if profile:
            profile = loads(profile)
            if profile.get('identifier'):
                if self.validIdentifier(profile) and not self.userOnline(profile['codename']):
                    connection.send(dumps(profile).encode())
                    self.loginUser(connection, profile['codename'])
                else:
                    connection.close()
            elif not self.codenameExists(profile['codename']):
                profile['identifier'] = self.createNewIdentifier()
                connection.send(dumps(profile).encode())
                self.saveUserProfile(profile)
                self.loginUser(connection, profile['codename'])
            else:
                connection.close()
        else:
            connection.close()
    
    def listenUserMessages(self, connection, codename):
        self.sendMessageTo(connection, f' Olá {codename}, seja bem-vindo à Mutiny!')

        while True:
            userOnline = connection.recv(2048)
            if userOnline:
                data = loads(userOnline)
                if not data['message'].startswith('/'):
                    data = dumps(data).encode()
                    if not self.connectedUsers[codename]['onPrivate']:
                        self.sendMessageToEveryone(connection, data)
                    else:
                        self.connectedUsers[codename]['onPrivate']['connectionAddress'].send(data)
                else:
                    self.checkCommand(connection, data)
            else:
                if self.onPrivate(codename):
                    self.removeUsersFromPrivate([self.connectedUsers[codename]['onPrivate']['codename']])
                    self.sendMessageTo(self.connectedUsers[codename]['onPrivate']['connectionAddress'], f'@{codename} deixou a sala privada com você. Voltando ao chat geral!')

                self.connectedUsers.pop(codename)
                self.showServerInfo()
                break
    
    def sendMessageToEveryone(self, sender, message):
        for user in self.connectedUsers.values():
            if user['connectionAddress'] is not sender and not user['onPrivate']:
                user['connectionAddress'].send(message)

    def sendMessageTo(self, user, message):
        data = {"codename": "Servidor", "nameColor": "green", "message": message}
        user.send(dumps(data).encode())
    
    def sendVersion(self, user, params):
        self.sendMessageTo(user, params['description'])

    def sendContact(self, user, params):
        self.sendMessageTo(user, params['description'])

    def sendCodeAuthor(self, user, params):
        self.sendMessageTo(user, params['description'])
    
    def addUserToPrivate(self, codenames):
        self.connectedUsers[codenames[0]]['onPrivate'].update({"codename": codenames[1], "connectionAddress": self.connectedUsers[codenames[1]]['connectionAddress']})
        self.connectedUsers[codenames[1]]['onPrivate'].update({"codename": codenames[0], "connectionAddress": self.connectedUsers[codenames[0]]['connectionAddress']})

    def acceptPrivateInvite(self, user, params):
        if params['functionArgs']:
            if not self.onPrivate(params['userData']['codename']):
                if self.onWaitRoom(params['userData']['codename']):
                    invite = self.openInvite(params["userData"]["codename"])
                    
                    if params['functionArgs'][0] in invite.get('invitationFrom'):
                        invite.get('invitationFrom').remove(params['functionArgs'][0])
                        if invite.get('invitationFrom'):
                            self.updateInvite(params["userData"]["codename"], invite)
                        else:
                            self.removeUserFromWaitroom(params["userData"]["codename"])

                        self.addUserToPrivate((params["userData"]["codename"], params["functionArgs"][0]))
                        self.sendMessageTo(user, f'Você está em uma sala privada com @{params["functionArgs"][0]} agora!')
                        self.sendMessageTo(self.connectedUsers[params['functionArgs'][0]]['connectionAddress'], f'@{params["userData"]["codename"]} aceitou seu pedido, você está em uma sala privada agora!')
                    else:
                        self.sendMessageTo(user, f'Você não recebeu nenhum convite de @{params["functionArgs"][0]}...')
                else:
                    self.sendMessageTo(user, 'Parece que você não recebeu nenhum convite para sala privada...')
            else:
                self.sendMessageTo(user, 'Você não pode aceitar um convite porque já está em uma sala privada...')
        else:
            self.sendMessageTo(user, params['description'])
        
    def createPrivateInvite(self, user, params):
        if params['functionArgs']:
            if not self.onPrivate(params['userData']['codename']):
                if params['userData']['codename'] != params['functionArgs'][0]:
                    if self.userOnline(params['functionArgs'][0]):
                        if not self.onWaitRoom(params['functionArgs'][0]):
                            invite = {"invitationFrom": [params['userData']['codename']]}
                            self.updateInvite(params["functionArgs"][0], invite)

                            if not self.onPrivate(params['functionArgs'][0]):
                                message = f' Olá {params["functionArgs"][0]}, o usuário @{params["userData"]["codename"]} quer se conectar com você!\n   Para aceitar digite /accept {params["userData"]["codename"]}'
                                self.sendMessageTo(self.connectedUsers.get(params["functionArgs"][0])['connectionAddress'], message)
                                self.sendMessageTo(user, f'Pedido enviado à @ {params["functionArgs"][0]}!')
                        else:
                            invite = self.openInvite(params["functionArgs"][0])

                            if params['userData']['codename'] not in invite.get('invitationFrom'):
                                invite.get('invitationFrom').append(params['userData']['codename'])
                                self.updateInvite(params["functionArgs"][0], invite)

                                if not self.onPrivate(params['functionArgs'][0]):
                                    message = f' Olá {params["functionArgs"][0]}, o usuário @{params["userData"]["codename"]} quer se conectar com você!\n   Para aceitar digite /accept {params["userData"]["codename"]}'
                                    self.sendMessageTo(self.connectedUsers.get(params["functionArgs"][0])['connectionAddress'], message)
                                    self.sendMessageTo(user, f'Pedido enviado à @ {params["functionArgs"][0]}!')
                    else:
                        self.sendMessageTo(user, f'O usuário @{params["functionArgs"][0]} não está online no momento...')
                else:
                    self.sendMessageTo(user, f'Você não pode mandar convite a sí mesmo...')
            else:
                self.sendMessageTo(user, 'Você não pode mandar um convite porque já está em uma sala privada...')
        else:
            self.sendMessageTo(user, params['description'])

    def cancelPrivateInvite(self, user, params):
        if params['functionArgs']:
            if self.onWaitRoom(params["functionArgs"][0]):
                invite = self.openInvite(params["functionArgs"][0])

                if params['userData']['codename'] in invite.get('invitationFrom'):
                    invite.get('invitationFrom').remove(params['userData']['codename'])
                    if invite.get('invitationFrom'):
                        self.updateInvite(params["functionArgs"][0], invite)
                    else:
                        self.removeUserFromWaitroom(params["functionArgs"][0])

                    self.sendMessageTo(user, f'Convite para @{params["functionArgs"][0]} removido!')
                    if self.userOnline(params["functionArgs"][0]):
                        self.sendMessageTo(self.connectedUsers[params['functionArgs'][0]]['connectionAddress'], f'O usuário @{params["userData"]["codename"]} cancelou o convite para sala privada com você.')
                else:
                    self.sendMessageTo(user, f'Você não enviou nenhum convite à @{params["functionArgs"][0]}!')
            else:
                self.sendMessageTo(user, f'Você não enviou nenhum convite à @{params["functionArgs"][0]}!')
        else:
            self.sendMessageTo(user, params['description'])
    
    def createWaitRoomFolder(self):
        if not Path('.server/waitRoom').is_dir(): Path('.server/waitRoom').mkdir(parents=True)
    
    def declinePrivateInvite(self, user, params):
        if params['functionArgs']:
            if self.onWaitRoom(params['userData']['codename']):
                invite = self.openInvite(params['userData']['codename'])
                if params['functionArgs'][0] in invite.get('invitationFrom'):
                    invite.get('invitationFrom').remove(params['functionArgs'][0])
                    if invite.get('invitationFrom'):
                        self.updateInvite(params['userData']['codename'], invite)
                    else:
                        self.removeUserFromWaitroom(params['userData']['codename'])
                    
                    self.sendMessageTo(user, f'Convite de @{params["functionArgs"][0]} foi removido!')
                    self.sendMessageTo(self.connectedUsers[params['functionArgs'][0]]['connectionAddress'], f'@{params["userData"]["codename"]} recusou o seu pedido para sala privada...')
                else:
                    self.sendMessageTo(user, f'Você não recebeu nenhum convite de @{params["functionArgs"][0]}...')
            else:
                self.sendMessageTo(user, 'Parece que você não tem nenhum convite para sala privada...')
        else:
            self.sendMessageTo(user, params['description'])
    
    def leaveFromPrivate(self, user, params):
        if self.onPrivate(params['userData']['codename']):
            codenames = (params['userData']['codename'], self.connectedUsers[params['userData']['codename']]['onPrivate']['codename'])

            self.sendMessageTo(self.connectedUsers[codenames[0]]['onPrivate']['connectionAddress'], f'@{codenames[0]} deixou a sala privada com você. Voltando ao chat geral!')
            self.removeUsersFromPrivate(codenames)
            self.sendMessageTo(user, f'Você deixou a sala com @{codenames[1]}. Voltando ao chat geral!')
        else:
            self.sendMessageTo(user, f'Você não está em uma sala privada no momento.')
    
    def onWaitRoom(self, codename):
        if Path(f'.server/waitRoom/{codename}.json').is_file():
            return True

    def onPrivate(self, codename):
        if self.connectedUsers[codename]['onPrivate']:
            return True
    
    def openInvite(self, codename):
        with open(f'.server/waitRoom/{codename}.json', 'rb') as inviteFile:
            return loads(inviteFile.read())
    
    def removeUsersFromPrivate(self, codenames):
        for user in codenames:
            self.connectedUsers[user]['onPrivate'] = {}
    
    def removeUserFromWaitroom(self, codename):
        Path(f'.server/waitRoom/{codename}.json').unlink()
    
    def receivedInvites(self, user, params):
        if Path(f'.server/waitRoom/{params["userData"]["codename"]}.json').is_file():
            invite = self.openInvite(params["userData"]["codename"])
            if invite.get('invitationFrom'):
                invites = invite.get('invitationFrom')
                if len(invites) > 1:
                    message = f'Você tem convite de {len(invites)} pessoas.\n' + ''.join(f'@{name}, ' for name in invites[:len(invites)-1]) + f'e @{invites[len(invites)-1]}.'
                    self.sendMessageTo(user, message)
                else:
                    self.sendMessageTo(user, f'Você tem um convite de @{invites[0]}!')
            else:
                self.sendMessageTo(user, 'Parece que você ainda não têm nenhum convite ;(')
        else:
            self.sendMessageTo(user, 'Parece que você ainda não têm nenhum convite ;(')
    
    def removeWaitRoomFolder(self):
        if Path('.server/waitRoom').is_dir(): rmtree('.server/waitRoom')
    
    def updateInvite(self, codename, invite):
        with open(f'.server/waitRoom/{codename}.json', 'w') as inviteFile:
            inviteFile.write(dumps(invite))
    
    def run(self):
        try:
            self.__server = self.configureSocketConnection()
        except Exception as err:
            print(colored(f'Erro: {err}', 'red')) & exit(1)
        finally:
            self.createRegistredUsersFolder()
            self.createWaitRoomFolder()
            self.showServerInfo()
            self.listenConnections()



def main():
    server = Server()
    server.run()

if __name__ == '__main__':
    main()
