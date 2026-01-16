-- Author: Rohan Vardekar

war_protocol = Proto("WAR",  "WAR Protocol")
Command = ProtoField.string("WAR.Command", "Command", base.ASCII)
Cards = ProtoField.string("WAR.Cards", "Cards", base.ASCII)
Result = ProtoField.string("WAR.Result", "Result", base.ASCII)
war_protocol.fields = {Command,Cards,Result}

function war_protocol.dissector(buffer, pinfo, tree)
  local length = buffer:len()
  if length == 0 then return end
  -- Name the column if has payload
  pinfo.cols.protocol = war_protocol.name

  local subtree = tree:add(war_protocol, buffer(), "WAR Protocol")
  local cmd = buffer(0,1):uint() -- (Starting Index,Length)
  if( cmd == 0 )then
    subtree:add(Command,"Want Game("..cmd..")")
    pinfo.cols.info = "Want Game"
    -- ignoring the second byte
  elseif( cmd == 1 )then
    subtree:add(Command,"Game Start("..cmd..")")
    -- cards from the server, array of 26 cards
    pinfo.cols.info = "Game Start"
    local cards = ""
    for itr=1,(length-1),1 do
      cards = cards..buffer(itr,1):uint()..","
    end
    subtree:add(Cards,"["..cards.."]")
  elseif( cmd == 2 )then
    pinfo.cols.info = "Play Card"
    subtree:add(Command,"Play Card("..cmd..")")
    -- card, but for convenience [card]
    local cards = buffer(1,1):uint()
    subtree:add(Cards,"["..cards.."]")
  elseif( cmd == 3 )then
    pinfo.cols.info = "Play Result"
    subtree:add(Command,"Play Result("..cmd..")") 
    -- result announcement
    
    local result = buffer(1,1):uint()
    if( result == 0 )then
      subtree:add(Result,"Win("..result..")")
    elseif( result == 1 )then
      subtree:add(Result,"Draw("..result..")")
    elseif( result == 2 )then
      subtree:add(Result,"Lose("..result..")")
    end

  end

end

local proto = DissectorTable.get("tcp.port")
proto:add(4444, war_protocol) -- Change to appropriate port number of server