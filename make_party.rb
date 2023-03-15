#!/usr/bin/ruby

# manymissions

# TODO
# - site_at should kinda work

require 'date'

def party filename, ct, timeframe, options
  arc = options[:arc]
  sites = options[:sites]
  vs = Vignette.load_many(filename)
  puts "loaded: #{vs.size}"
  duration = timeframe.end - timeframe.begin
  time_each = duration / ct
  t0 = timeframe.begin
  acc = []
  arc.each do |percent, tag|
    (percent * ct).to_i.times do
      picked = pick_matching(vs, tag)
      raise "too few matching: #{tag}" unless picked
      picked.time = t0
      picked.site_at(sites)
      t0 += time_each
      acc << picked
    end
  end

  output = open("| enscript -U8 --word-wrap -f Times-Roman36 -B -p #{filename}.cards.ps", 'w')
  output.puts acc.map(&:to_cards).join
rescue Exception => e
  puts e
end

def pick_matching vs, tag
  matching = vs.select{ |v| v.tags.include?(tag) }
  puts "#{vs.count} match #{tag}"
  obj = matching.shuffle.first
  vs.delete(obj)
end

def list vs
  vs.each_with_index do |v, i| puts v.to_s(i+1) end
end

def roles vs
  puts vs.map{ |v| v.to_roles }.join
end

def cards vs
  puts vs.map{ |v| v.to_cards }.join
end

def places vs
  puts vs.map{ |v| v.place.strip }.uniq.join("\n")
end

def props vs
  puts vs.map{ |v| v.roles.map{ |r| r.instructions.match(/\[(.*)\]/) && $1.downcase }.compact! }.flatten.compact.uniq.join("\n")
end

class Role < Struct.new :instructions, :count, :offset
  def to_s
    str = "- #{instructions}"
    str << " (x#{count})"  unless count == 1
    str << " (#{offset}m)" unless offset == 0
    str
  end

  def to_cards(place, time)
    t = time.to_time.utc + offset*60
    t = t.strftime("%l:%M")
    # modifier = if offset == 0 then '' elsif offset > 0; "#{offset.abs} minutes after " else "#{offset.abs} minutes before " end
    "WHEN: #{t}\nWHERE: #{place}\n\n#{instructions}\n\f" * count
  end

  def to_roles(place, time)
    "#{offset} // #{instructions}\n" * count
  end
end

class Vignette < Struct.new :tags, :roles, :time, :place
  def self.load(str)
    first_line, *rest = str.split(/\n-\s+/)
    tags, comment = *first_line.split('//')
    tags = tags.split(' ')
    roles = rest.map do |role_line|
      role_line.chomp!
      count = 1
      if role_line.sub!(/\(x(\d+)\)/, '') or role_line.sub!(/(\d+)x\.?\s*$/,'') or role_line.sub!(/x(\d+)\.?\s*$/,'')
        count = $1.to_i
      end
      offset = 0
      if role_line.sub!(/\(\+?(\-?\d+)m?\)/, '')
        offset = $1.to_i
      end
      Role.new(role_line, count, offset)
    end
    new(tags, roles, nil, nil)
  end

    # "in the kitchen" => { starts: '7:30pm', every: '10m', tags: %w{ intimate anywhere } },
  def site_at(sites = {})
    self.place = sites.keys.shuffle.find do |key|
      sites[key][:tags].any?{ |t| tags.include?(t) }
    end
    return if self.place
    raise "unable to site: #{self.inspect}"

    self.place = sites.keys.shuffle.first
    return

    placetag = tags.find{ |t| t =~ /^@/ }
    return sites[placetag.slice(1..-1)] if placetag
    return sites.values.shuffle.first
  end

  def roles_str
    roles.each{ |r| r.to_s }.join("\n")
  end

  def to_s(num)
    str = "##{num} #{tags.join(' ')}"
    str << " // #{place} // #{time}" if place or time
    str << "\n#{roles_str}\n\n"
    str
  end

  def self.load_many(filename)
    File.open(filename).read.split(/^\s*$/).map{ |pp| load(pp) }.compact
  end

  def to_cards
    roles.map{ |r| r.to_cards(place, time) }.join
    # | enscript -U8 --word-wrap -f Times-Roman36 -B -p cards.ps
  end

  def to_roles
    roles.map{ |r| r.to_roles(place, time) }.join
  end
end

# if __FILE__ == $0
#   meth = ARGV.shift
#   fn = ARGV.shift
#   tags = ARGV
#   vs = Vignette.load_many(fn)
#   if !tags.empty?
#     vs = vs.select{ |v| tags.all?{ |t| v.tags.include?(t) } }
#   end
#   send meth, vs
# end



party 'birthday_2023_missions.txt', 30, DateTime.parse('1:00pm')..DateTime.parse('6:00pm'), \
  starts: '1:00pm',
  ends: '6:00pm',
  sites: {
    "in the kitchen" => { starts: '7:30pm', every: '10m', tags: %w{ intimate anywhere } },
    "in the yoga studio" => { starts: '7:30pm', every: '10m', tags: %w{ large anywhere } },
    "by the downstairs bathroom door" => { starts: '7:30pm', every: '10m', tags: %w{ rendezvous } },
    "on the landing at the top of the west stairs" => { tags: ['entryway'] },
    "seated on the couch by the stained glass" => { tags: ['seated'] }
  },
  arc: [
    [0.1, 'foreshadowing'],
    [0.1, 'kickoff'],
    [0.4, 'rolling'],
    [0.3, 'risky'],
    [0.1, 'finale']
  ]
