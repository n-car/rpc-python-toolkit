from rpc_python_toolkit import RpcEndpoint


rpc = RpcEndpoint(enable_introspection=True)


def test(_request, _context, params):
    return {
        "ok": True,
        "params": params,
    }


rpc.add_method("test", test)


if __name__ == "__main__":
    response = rpc.handle_request(
        {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"value": 123},
            "id": 1,
        }
    )
    print(response)

