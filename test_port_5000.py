#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试端口 5000 连接的工具脚本
可以用于测试端口是否开放，或者作为简单的客户端连接到服务
"""

import socket
import sys
import time


def test_port(host='localhost', port=5000, timeout=3):
    """测试端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ 端口 {port} 已开放，可以连接")
            return True
        else:
            print(f"✗ 端口 {port} 未开放或无法连接 (错误代码: {result})")
            return False
    except socket.timeout:
        print(f"✗ 连接超时：端口 {port} 无响应")
        return False
    except socket.gaierror:
        print(f"✗ 主机名解析失败：{host}")
        return False
    except Exception as e:
        print(f"✗ 连接错误: {e}")
        return False


def connect_interactive(host='localhost', port=5000):
    """交互式连接到端口（类似 telnet）"""
    try:
        print(f"正在连接到 {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print(f"✓ 已连接到 {host}:{port}")
        print("输入数据发送到服务器，输入 'quit' 或按 Ctrl+C 退出\n")
        
        sock.settimeout(0.5)  # 设置较短的超时以便检查输入
        
        while True:
            try:
                # 检查是否有数据可读
                ready = socket.select([sock], [], [], 0.5)[0]
                if ready:
                    data = sock.recv(1024)
                    if not data:
                        print("\n连接已关闭")
                        break
                    print(f"收到: {data.decode('utf-8', errors='ignore')}", end='')
                
                # 检查用户输入（非阻塞）
                if sys.stdin in socket.select([sys.stdin], [], [], 0)[0]:
                    user_input = input()
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    sock.sendall((user_input + '\n').encode('utf-8'))
                    
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                print("\n\n中断连接...")
                break
                
        sock.close()
        print("连接已关闭")
        
    except socket.timeout:
        print(f"✗ 连接超时：无法连接到 {host}:{port}")
    except ConnectionRefusedError:
        print(f"✗ 连接被拒绝：{host}:{port} 没有服务在监听")
    except Exception as e:
        print(f"✗ 连接错误: {e}")


def create_test_server(port=5000):
    """创建一个测试服务器（用于测试 telnet 连接）"""
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', port))
        server.listen(1)
        print(f"测试服务器已启动，监听端口 {port}")
        print("等待客户端连接...")
        print("按 Ctrl+C 停止服务器\n")
        
        while True:
            client, addr = server.accept()
            print(f"客户端已连接: {addr}")
            client.sendall(b"欢迎连接到测试服务器！\n")
            client.sendall(b"输入 'quit' 断开连接\n")
            
            while True:
                try:
                    data = client.recv(1024)
                    if not data:
                        break
                    message = data.decode('utf-8', errors='ignore').strip()
                    print(f"收到: {message}")
                    
                    if message.lower() == 'quit':
                        client.sendall(b"再见！\n")
                        break
                    else:
                        client.sendall(f"回显: {message}\n".encode('utf-8'))
                        
                except Exception as e:
                    print(f"错误: {e}")
                    break
            
            client.close()
            print(f"客户端 {addr} 已断开\n")
            
    except KeyboardInterrupt:
        print("\n\n正在关闭服务器...")
    except OSError as e:
        if e.errno == 10048:  # Windows: Address already in use
            print(f"✗ 端口 {port} 已被占用")
        else:
            print(f"✗ 错误: {e}")
    finally:
        try:
            server.close()
        except:
            pass


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='测试端口 5000 连接工具')
    parser.add_argument('--host', default='localhost', help='目标主机 (默认: localhost)')
    parser.add_argument('--port', type=int, default=5000, help='目标端口 (默认: 5000)')
    parser.add_argument('--test', action='store_true', help='仅测试端口是否开放')
    parser.add_argument('--connect', action='store_true', help='交互式连接到端口')
    parser.add_argument('--server', action='store_true', help='启动测试服务器')
    
    args = parser.parse_args()
    
    if args.server:
        create_test_server(args.port)
    elif args.connect:
        connect_interactive(args.host, args.port)
    else:
        test_port(args.host, args.port)

